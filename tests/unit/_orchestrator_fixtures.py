"""Shared fixtures for the orchestrator test files. Filename starts with `_`
so pytest does not try to collect it as a test module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from debate.shared.schemas import OpeningBrief, Ping, Score, Verdict, YourTurn

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


def ping(side: str, round_: int) -> Ping:
    return Ping(
        round=round_,
        side=side,
        text=f"{side} round {round_}",
        timestamp=NOW,
        refers_to_ping=(round_ - 1 if side == "cats" or round_ > 1 else None),
    )


def mock_agent(side: str):
    """Agent that emits a deterministic Ping for whatever YourTurn it's given."""
    agent = MagicMock()

    def receive(env):
        if isinstance(env, OpeningBrief):
            return None
        if isinstance(env, YourTurn):
            return ping(side, env.round)
        return None

    agent.receive.side_effect = receive
    return agent


def mock_judge():
    judge = MagicMock()
    judge.scores = []

    def receive(env):
        if isinstance(env, OpeningBrief):
            return None
        if isinstance(env, Ping):
            score = Score(
                ping_round=env.round,
                side=env.side,
                structure=2,
                logos=2,
                pathos=2,
                ethos=2,
                clash=2,
                rationale="ok",
            )
            judge.scores.append(score)
            return score
        return Verdict(
            winner="dogs",
            dogs_total=20,
            cats_total=18,
            margin=2,
            written_rationale="dogs edged it",
            key_points_dogs=["loyalty"],
            key_points_cats=["independence"],
        )

    judge.receive.side_effect = receive
    return judge
