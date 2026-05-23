"""Shared fixtures for the CLI test files. Filename starts with `_` so
pytest does not collect it."""

from __future__ import annotations

from datetime import datetime, timezone

from debate.shared.schemas import DebateResult, Ping, Verdict


def verdict(winner: str = "dogs") -> Verdict:
    return Verdict(
        winner=winner,
        dogs_total=10,
        cats_total=8,
        margin=2,
        written_rationale="solid case",
        key_points_dogs=[],
        key_points_cats=[],
    )


def result() -> DebateResult:
    now = datetime.now(timezone.utc)
    return DebateResult(
        topic="t",
        pings=[
            Ping(
                round=1,
                side="dogs",
                text="open",
                citations=["url"],
                refers_to_ping=None,
                timestamp=now,
                tokens_in=5,
                tokens_out=5,
            ),
        ],
        scores=[],
        verdict=verdict(),
        cost_report={"total_usd": 0.01},
        started_at=now,
        finished_at=now,
    )


class FakeReader:
    """Deterministic stand-in for `input` — returns canned strings in order."""

    def __init__(self, inputs: list[str]) -> None:
        self.inputs = list(inputs)

    def __call__(self, _prompt: str) -> str:
        return self.inputs.pop(0)


class CapturingWriter:
    """Stand-in for `print` that collects lines for assertion."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, msg: str) -> None:
        self.lines.append(str(msg))

    @property
    def all(self) -> str:
        return "\n".join(self.lines)
