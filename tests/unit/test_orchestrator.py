"""Orchestrator tests (Phase 3.9)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from debate.services.orchestrator import Orchestrator
from debate.shared.schemas import (
    DebateResult,
    OpeningBrief,
    Ping,
    Score,
    Verdict,
    YourTurn,
)

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


def _ping(side: str, round_: int) -> Ping:
    return Ping(
        round=round_, side=side, text=f"{side} round {round_}", timestamp=NOW,
        refers_to_ping=(round_ - 1 if side == "cats" or round_ > 1 else None),
    )


def _mock_agent(side: str):
    """Agent that emits a deterministic Ping for whatever YourTurn it's given."""
    agent = MagicMock()
    def receive(env):
        if isinstance(env, OpeningBrief):
            return None
        if isinstance(env, YourTurn):
            return _ping(side, env.round)
        return None
    agent.receive.side_effect = receive
    return agent


def _mock_judge():
    judge = MagicMock()
    judge.scores = []
    def receive(env):
        if isinstance(env, OpeningBrief):
            return None
        if isinstance(env, Ping):
            score = Score(
                ping_round=env.round, side=env.side,
                structure=2, logos=2, pathos=2, ethos=2, clash=2, rationale="ok",
            )
            judge.scores.append(score)
            return score
        # FinalizeRequest
        return Verdict(
            winner="dogs", dogs_total=20, cats_total=18, margin=2,
            written_rationale="dogs edged it",
            key_points_dogs=["loyalty"], key_points_cats=["independence"],
        )
    judge.receive.side_effect = receive
    return judge


def test_orchestrator_run_debate_smoke(tmp_path: Path):
    orch = Orchestrator(topic="t", num_rounds=2, results_dir=tmp_path)
    result = orch.run_debate(_mock_agent("dogs"), _mock_agent("cats"), _mock_judge())
    assert isinstance(result, DebateResult)
    assert result.verdict.winner == "dogs"
    assert len(result.pings) == 4  # 2 rounds × 2 sides
    assert len(result.scores) == 4


def test_orchestrator_dogs_opens_round_1(tmp_path: Path):
    """Per PRD §3.2.1 Dogs always produces the first ping of round 1."""
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path)
    dogs, cats, judge = _mock_agent("dogs"), _mock_agent("cats"), _mock_judge()
    orch.run_debate(dogs, cats, judge)
    # First non-brief call to dogs must be YourTurn(round=1, previous_ping=None)
    your_turn_calls = [c for c in dogs.receive.call_args_list if isinstance(c.args[0], YourTurn)]
    first = your_turn_calls[0].args[0]
    assert first.round == 1
    assert first.previous_ping is None


def test_orchestrator_judge_receives_every_ping(tmp_path: Path):
    orch = Orchestrator(topic="t", num_rounds=3, results_dir=tmp_path)
    dogs, cats, judge = _mock_agent("dogs"), _mock_agent("cats"), _mock_judge()
    orch.run_debate(dogs, cats, judge)
    ping_calls = [c for c in judge.receive.call_args_list if isinstance(c.args[0], Ping)]
    assert len(ping_calls) == 6  # 3 rounds × 2 pings


def test_orchestrator_persists_result_json(tmp_path: Path):
    orch = Orchestrator(topic="cats-vs-dogs", num_rounds=2, results_dir=tmp_path)
    result = orch.run_debate(_mock_agent("dogs"), _mock_agent("cats"), _mock_judge())
    files = list(tmp_path.glob("debate_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["verdict"]["winner"] == result.verdict.winner
    assert payload["topic"] == "cats-vs-dogs"


def test_orchestrator_broadcasts_opening_brief(tmp_path: Path):
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path)
    dogs, cats, judge = _mock_agent("dogs"), _mock_agent("cats"), _mock_judge()
    orch.run_debate(dogs, cats, judge)
    dogs_brief = dogs.receive.call_args_list[0].args[0]
    cats_brief = cats.receive.call_args_list[0].args[0]
    judge_brief = judge.receive.call_args_list[0].args[0]
    assert isinstance(dogs_brief, OpeningBrief) and dogs_brief.side == "dogs"
    assert isinstance(cats_brief, OpeningBrief) and cats_brief.side == "cats"
    assert isinstance(judge_brief, OpeningBrief) and judge_brief.side is None
    assert judge_brief.rubric is not None


def test_orchestrator_raises_when_agent_returns_non_ping(tmp_path: Path):
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path)
    broken = MagicMock()
    broken.receive.return_value = "not a ping"
    with pytest.raises(RuntimeError, match="did not return a Ping"):
        orch.run_debate(broken, _mock_agent("cats"), _mock_judge())


def test_orchestrator_cats_sees_dogs_ping_as_previous(tmp_path: Path):
    """Within a round, Cats receives Dogs' fresh ping as previous_ping (not the
    prior round's). This is the chain that makes clash possible in round 1."""
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path)
    dogs, cats, judge = _mock_agent("dogs"), _mock_agent("cats"), _mock_judge()
    orch.run_debate(dogs, cats, judge)
    cats_turn_call = [c for c in cats.receive.call_args_list if isinstance(c.args[0], YourTurn)][0]
    prev = cats_turn_call.args[0].previous_ping
    assert prev is not None and prev.side == "dogs" and prev.round == 1
