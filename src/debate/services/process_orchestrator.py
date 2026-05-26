"""Multiprocessing orchestrator with Queue IPC and watchdog heartbeats."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from debate.services._orchestrator_helpers import (
    announcement_text,
    make_brief,
    persist_result,
    rubric_blurb,
)
from debate.services.agents.judge_agent import FinalizeRequest
from debate.services.process_runtime import ProcessRuntime, merge_costs
from debate.shared.config import SetupConfig
from debate.shared.schemas import DebateResult, Ping, Score, Side, Verdict, YourTurn


class ProcessOrchestrator:
    """Parent process: owns ordering, persistence, queues, and watchdog."""

    def __init__(
        self,
        setup: SetupConfig,
        results_dir: Path | str = "results/debates",
        rate_limits_path: str | Path = "config/rate_limits.json",
        logging_path: str | Path = "config/logging_config.json",
        on_event=None,
        coin_flip=lambda: random.randint(0, 1),
    ) -> None:
        self.setup = setup
        self.results_dir = Path(results_dir)
        self.on_event = on_event
        self.coin_flip = coin_flip
        self.pings: list[Ping] = []
        self.scores: list[Score] = []
        self.runtime = ProcessRuntime(setup, rate_limits_path, logging_path)

    def run_debate(self) -> DebateResult:
        started_at = datetime.now(timezone.utc)
        self.runtime.start_all()
        closed = False
        try:
            self._brief_all()
            opener: Side = "dogs" if self.coin_flip() == 1 else "cats"
            self._emit(
                "announcement",
                announcement_text(self.setup.topic, self._rules(), self.setup.num_rounds, opener),
            )
            first, second = ("dogs", "cats") if opener == "dogs" else ("cats", "dogs")
            previous: Ping | None = None
            for round_num in range(1, self.setup.num_rounds + 1):
                previous = self._round(first, second, round_num, previous)
            verdict = self._verdict()
            self.runtime.shutdown()
            closed = True
            result = DebateResult(
                topic=self.setup.topic,
                pings=self.pings,
                scores=self.scores,
                verdict=verdict,
                cost_report=merge_costs(self.runtime.costs),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
            persist_result(result, self.results_dir)
            return result
        finally:
            if not closed:
                self.runtime.shutdown()

    def _brief_all(self) -> None:
        rules = self._rules()
        topic, rounds = self.setup.topic, self.setup.num_rounds
        self.runtime.send("dogs", make_brief(topic, rounds, rules, side="dogs"))
        self.runtime.send("cats", make_brief(topic, rounds, rules, side="cats"))
        self.runtime.send(
            "judge",
            make_brief(topic, rounds, rules, side=None, rubric=rubric_blurb()),
        )

    def _round(self, first: str, second: str, round_num: int, previous: Ping | None) -> Ping:
        first_ping = self._ask_ping(first, round_num, previous)
        self._score(first_ping)
        second_ping = self._ask_ping(second, round_num, first_ping)
        self._score(second_ping)
        return second_ping

    def _ask_ping(self, agent_id: str, round_num: int, previous: Ping | None) -> Ping:
        self.runtime.send(agent_id, YourTurn(round=round_num, previous_ping=previous))
        ping = self.runtime.recv(agent_id)
        if not isinstance(ping, Ping):
            raise RuntimeError(f"{agent_id} did not return Ping")
        self.pings.append(ping)
        self._emit("ping", ping)
        return ping

    def _score(self, ping: Ping) -> None:
        self.runtime.send("judge", ping)
        score = self.runtime.recv("judge")
        if isinstance(score, Score):
            self.scores.append(score)
            self._emit("score", score)

    def _verdict(self) -> Verdict:
        self.runtime.send("judge", FinalizeRequest(self.pings))
        verdict = self.runtime.recv("judge")
        if not isinstance(verdict, Verdict):
            raise RuntimeError("judge did not return Verdict")
        self._emit("verdict", verdict)
        return verdict

    def _rules(self) -> str:
        return "<=250 words per ping, JSON-only replies, clash required from round 2."

    def _emit(self, kind: str, payload: Any) -> None:
        if self.on_event is not None:
            self.on_event(kind, payload)
