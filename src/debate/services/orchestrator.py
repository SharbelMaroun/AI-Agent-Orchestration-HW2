"""Orchestrator — drives the debate loop. See docs/PRD.md §3.2.

Runs three agents synchronously by calling `agent.receive(envelope)`
directly. The same agents can later be hosted in `multiprocessing.Process`es
with a thin queue adapter — the agent contract is unchanged. ADR note:
deliberate Phase 3.9 trade-off documented in `docs/PROMPTS.md`.

The opener of round 1 is decided by a coin flip (`1 → dogs`, `0 → cats`)
via the injected `coin_flip` callable; tests pass a deterministic flip.
Before round 1, the orchestrator emits an `announcement` event labelled
as coming from the Judge (templated, no extra LLM call) so the user sees
the rules + opener choice in the live event stream.
"""

from __future__ import annotations

import random
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
    Side,
    Verdict,
    YourTurn,
)

OnEvent = Callable[[str, Any], None]  # kind in {announcement, ping, score, verdict}
CoinFlip = Callable[[], int]  # returns 0 (cats opens) or 1 (dogs opens)


class Orchestrator:
    """Single-process driver. Runs `num_rounds` rounds, then asks Judge for verdict."""

    def __init__(
        self,
        topic: str,
        num_rounds: int,
        rules: str = "≤250 words per ping, JSON-only replies, clash required from round 2.",
        results_dir: Path | str = "results/debates",
        on_event: OnEvent | None = None,
        coin_flip: CoinFlip = lambda: random.randint(0, 1),
        models: dict | None = None,
        pricing: dict | None = None,
    ) -> None:
        self.topic = topic
        self.num_rounds = num_rounds
        self.rules = rules
        self.results_dir = Path(results_dir)
        self.on_event = on_event
        self.coin_flip = coin_flip
        self.models = models or {}
        self.pricing = pricing or {}
        self.pings: list[Ping] = []

    def _emit(self, kind: str, payload: Any) -> None:
        if self.on_event is not None:
            self.on_event(kind, payload)

    def run_debate(self, dogs: Any, cats: Any, judge: JudgeAgent) -> DebateResult:
        started_at = datetime.now(timezone.utc)
        self._broadcast_opening_brief(dogs, cats, judge)
        opener: Side = "dogs" if self.coin_flip() == 1 else "cats"
        self._emit("announcement", self._announcement_text(opener))
        first, second = (dogs, cats) if opener == "dogs" else (cats, dogs)
        previous_ping: Ping | None = None
        for round_num in range(1, self.num_rounds + 1):
            first_ping, second_ping = self._run_round(
                first, second, judge, round_num, previous_ping
            )
            self.pings.extend([first_ping, second_ping])
            previous_ping = second_ping
        verdict = self._collect_verdict(judge)
        finished_at = datetime.now(timezone.utc)
        result = DebateResult(
            topic=self.topic,
            pings=self.pings,
            scores=list(judge.scores),
            verdict=verdict,
            cost_report=self._build_cost_report(),
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

    def _announcement_text(self, opener: Side) -> str:
        return (
            f'Judge: Welcome to the debate. Topic: "{self.topic}". '
            f"Rules: {self.rules} The debate runs for {self.num_rounds} round(s). "
            f"Coin flip result: {opener.upper()} will open."
        )

    def _build_cost_report(self) -> dict:
        """Delegates to `pricing.cost_report_from_pings` — lives in pricing.py
        so the math is reusable and orchestrator.py stays under the LOC cap."""
        from debate.shared.pricing import cost_report_from_pings

        return cost_report_from_pings(self.pings, self.models, self.pricing)

    @staticmethod
    def _rubric_blurb() -> str:
        return "Five dimensions per ping (Structure, Logos, Pathos, Ethos, Clash), 0-3 each."
