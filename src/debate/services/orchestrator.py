"""Orchestrator — drives the debate loop. See docs/PRD.md §3.2.

For now the loop runs the three agents synchronously by calling
`agent.receive(envelope)` directly (each agent's `receive` is already
designed to be a one-shot dispatch). The same agent instances can later be
hosted in `multiprocessing.Process`es with a thin queue adapter — the
agent contract (a `receive(envelope)` that returns the next envelope) does
not change. Keeping the loop synchronous here makes the orchestrator
trivially testable and the file fits under the 150-LOC cap.

ADR note: this is the deliberate Phase 3.9 trade-off documented in
docs/PROMPTS.md — synchronous orchestration first, process isolation if
and when the watchdog phase needs it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from debate.services.agents.judge_agent import FinalizeRequest, JudgeAgent
from debate.shared.schemas import (
    DebateResult,
    OpeningBrief,
    Ping,
    Score,
    Verdict,
    YourTurn,
)

OnEvent = Callable[[str, Any], None]  # (kind, payload) — kind in {"ping","score","verdict"}


class Orchestrator:
    """Single-process driver. Runs `num_rounds` rounds, then asks Judge for verdict."""

    def __init__(
        self,
        topic: str,
        num_rounds: int,
        rules: str = "≤250 words per ping, JSON-only replies, clash required from round 2.",
        results_dir: Path | str = "results/debates",
        on_event: OnEvent | None = None,
    ) -> None:
        self.topic = topic
        self.num_rounds = num_rounds
        self.rules = rules
        self.results_dir = Path(results_dir)
        self.on_event = on_event
        self.pings: list[Ping] = []

    def _emit(self, kind: str, payload: Any) -> None:
        if self.on_event is not None:
            self.on_event(kind, payload)

    def run_debate(self, dogs: Any, cats: Any, judge: JudgeAgent) -> DebateResult:
        started_at = datetime.now(timezone.utc)
        self._broadcast_opening_brief(dogs, cats, judge)
        previous_ping: Ping | None = None
        for round_num in range(1, self.num_rounds + 1):
            dogs_ping, cats_ping = self._run_round(dogs, cats, judge, round_num, previous_ping)
            self.pings.extend([dogs_ping, cats_ping])
            previous_ping = cats_ping
        verdict = self._collect_verdict(judge)
        finished_at = datetime.now(timezone.utc)
        result = DebateResult(
            topic=self.topic,
            pings=self.pings,
            scores=list(judge.scores),
            verdict=verdict,
            cost_report={},
            started_at=started_at,
            finished_at=finished_at,
        )
        self._persist_result(result)
        return result

    def _broadcast_opening_brief(self, dogs: Any, cats: Any, judge: JudgeAgent) -> None:
        dogs.receive(self._brief(side="dogs"))
        cats.receive(self._brief(side="cats"))
        judge.receive(self._brief(side=None, rubric=self._rubric_blurb()))

    def _run_round(
        self,
        dogs: Any,
        cats: Any,
        judge: JudgeAgent,
        round_num: int,
        previous_ping: Ping | None,
    ) -> tuple[Ping, Ping]:
        """Dogs opens; Cats responds. Judge scores each ping immediately."""
        dogs_ping = dogs.receive(YourTurn(round=round_num, previous_ping=previous_ping))
        if not isinstance(dogs_ping, Ping):
            raise RuntimeError(f"Dogs agent did not return a Ping in round {round_num}")
        self._emit("ping", dogs_ping)
        dogs_score = judge.receive(dogs_ping)
        if isinstance(dogs_score, Score):
            self._emit("score", dogs_score)

        cats_ping = cats.receive(YourTurn(round=round_num, previous_ping=dogs_ping))
        if not isinstance(cats_ping, Ping):
            raise RuntimeError(f"Cats agent did not return a Ping in round {round_num}")
        self._emit("ping", cats_ping)
        cats_score = judge.receive(cats_ping)
        if isinstance(cats_score, Score):
            self._emit("score", cats_score)
        return dogs_ping, cats_ping

    def _collect_verdict(self, judge: JudgeAgent) -> Verdict:
        verdict = judge.receive(FinalizeRequest(pings=self.pings))
        if not isinstance(verdict, Verdict):
            raise RuntimeError("Judge did not return a Verdict")
        self._emit("verdict", verdict)
        return verdict

    def _persist_result(self, result: DebateResult) -> Path:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        ts = result.started_at.strftime("%Y%m%dT%H%M%S")
        path = self.results_dir / f"debate_{ts}.json"
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return path

    def _brief(self, side: str | None, rubric: str | None = None) -> OpeningBrief:
        return OpeningBrief(
            topic=self.topic,
            num_rounds=self.num_rounds,
            rules=self.rules,
            side=side,
            rubric=rubric,
        )

    @staticmethod
    def _rubric_blurb() -> str:
        return "Five dimensions per ping (Structure, Logos, Pathos, Ethos, Clash), 0-3 each."
