"""Orchestrator — drives the debate loop. See docs/PRD.md §3.2.

Runs the three agents synchronously via `agent.receive(envelope)`. The
opener of round 1 is decided by a coin flip (`1 → dogs`, `0 → cats`).
Before round 1, the Judge emits an `announcement` event (templated, no
extra LLM call). Stateless helpers live in `_orchestrator_helpers.py`.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from debate.services._orchestrator_helpers import (
    announcement_text,
    build_cost_report,
    make_brief,
    persist_result,
    rubric_blurb,
)
from debate.services.agents.judge_agent import FinalizeRequest, JudgeAgent
from debate.shared.schemas import DebateResult, Ping, Score, Side, Verdict, YourTurn

OnEvent = Callable[[str, Any], None]
CoinFlip = Callable[[], int]  # 1 = dogs opens, 0 = cats opens


class Orchestrator:
    """Single-process driver. Runs `num_rounds` rounds, then asks Judge for verdict."""

    def __init__(
        self,
        topic: str,
        num_rounds: int,
        rules: str = "<=250 words per ping, JSON-only replies, clash required from round 2.",
        results_dir: Path | str = "results/debates",
        on_event: OnEvent | None = None,
        coin_flip: CoinFlip = lambda: random.randint(0, 1),
        models: dict | None = None,
        pricing: dict | None = None,
        cost_report_factory: Callable[[], dict] | None = None,
    ) -> None:
        self.topic = topic
        self.num_rounds = num_rounds
        self.rules = rules
        self.results_dir = Path(results_dir)
        self.on_event = on_event
        self.coin_flip = coin_flip
        self.models = models or {}
        self.pricing = pricing or {}
        self.cost_report_factory = cost_report_factory
        self.pings: list[Ping] = []

    def _emit(self, kind: str, payload: Any) -> None:
        if self.on_event is not None:
            self.on_event(kind, payload)

    def run_debate(self, dogs: Any, cats: Any, judge: JudgeAgent) -> DebateResult:
        started_at = datetime.now(timezone.utc)
        self._broadcast_opening_brief(dogs, cats, judge)
        opener: Side = "dogs" if self.coin_flip() == 1 else "cats"
        self._emit(
            "announcement", announcement_text(self.topic, self.rules, self.num_rounds, opener)
        )
        first, second = (dogs, cats) if opener == "dogs" else (cats, dogs)
        previous_ping: Ping | None = None
        for round_num in range(1, self.num_rounds + 1):
            first_ping, second_ping = self._run_round(
                first,
                second,
                judge,
                round_num,
                previous_ping,
            )
            self.pings.extend([first_ping, second_ping])
            previous_ping = second_ping
        verdict = self._collect_verdict(judge)
        result = DebateResult(
            topic=self.topic,
            pings=self.pings,
            scores=list(judge.scores),
            verdict=verdict,
            cost_report=self._build_cost_report(),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
        persist_result(result, self.results_dir)
        return result

    def _build_cost_report(self) -> dict:
        if self.cost_report_factory is not None:
            return self.cost_report_factory()
        return build_cost_report(self.pings, self.models, self.pricing)

    def _broadcast_opening_brief(self, dogs: Any, cats: Any, judge: JudgeAgent) -> None:
        dogs.receive(make_brief(self.topic, self.num_rounds, self.rules, side="dogs"))
        cats.receive(make_brief(self.topic, self.num_rounds, self.rules, side="cats"))
        judge.receive(
            make_brief(
                self.topic,
                self.num_rounds,
                self.rules,
                side=None,
                rubric=rubric_blurb(),
            )
        )

    def _run_round(
        self,
        first: Any,
        second: Any,
        judge: JudgeAgent,
        round_num: int,
        previous_ping: Ping | None,
    ) -> tuple[Ping, Ping]:
        """`first` opens; `second` responds. Judge scores each ping immediately."""
        first_ping = first.receive(YourTurn(round=round_num, previous_ping=previous_ping))
        if not isinstance(first_ping, Ping):
            raise RuntimeError(f"First agent did not return a Ping in round {round_num}")
        self._emit("ping", first_ping)
        first_score = judge.receive(first_ping)
        if isinstance(first_score, Score):
            self._emit("score", first_score)
        second_ping = second.receive(YourTurn(round=round_num, previous_ping=first_ping))
        if not isinstance(second_ping, Ping):
            raise RuntimeError(f"Second agent did not return a Ping in round {round_num}")
        self._emit("ping", second_ping)
        second_score = judge.receive(second_ping)
        if isinstance(second_score, Score):
            self._emit("score", second_score)
        return first_ping, second_ping

    def _collect_verdict(self, judge: JudgeAgent) -> Verdict:
        verdict = judge.receive(FinalizeRequest(pings=self.pings))
        if not isinstance(verdict, Verdict):
            raise RuntimeError("Judge did not return a Verdict")
        self._emit("verdict", verdict)
        return verdict
