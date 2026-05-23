"""Orchestrator core tests: round loop, briefing, persistence, error paths.

Event-streaming tests live in `test_orchestrator_events.py`. Coin-flip +
announcement tests live in `test_orchestrator_opener.py`. All three files
share fixtures from `_orchestrator_fixtures.py`. Split for the 150-LOC
test cap (CLAUDE.md §6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from debate.services.orchestrator import Orchestrator
from debate.shared.schemas import DebateResult, OpeningBrief, Ping, Score, Verdict, YourTurn
from tests.unit._orchestrator_fixtures import mock_agent, mock_judge


def test_run_debate_smoke(tmp_path: Path):
    orch = Orchestrator(topic="t", num_rounds=2, results_dir=tmp_path, coin_flip=lambda: 1)
    result = orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    assert isinstance(result, DebateResult)
    assert result.verdict.winner == "dogs"
    assert len(result.pings) == 4
    assert len(result.scores) == 4


def test_judge_receives_every_ping(tmp_path: Path):
    judge = mock_judge()
    orch = Orchestrator(topic="t", num_rounds=2, results_dir=tmp_path, coin_flip=lambda: 1)
    orch.run_debate(mock_agent("dogs"), mock_agent("cats"), judge)
    ping_calls = [c for c in judge.receive.call_args_list if isinstance(c.args[0], Ping)]
    assert len(ping_calls) == 4


def test_persists_result_json(tmp_path: Path):
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path, coin_flip=lambda: 1)
    orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    files = list(tmp_path.glob("debate_*.json"))
    assert len(files) == 1
    DebateResult.model_validate(json.loads(files[0].read_text(encoding="utf-8")))


def test_broadcasts_opening_brief(tmp_path: Path):
    dogs, cats, judge = mock_agent("dogs"), mock_agent("cats"), mock_judge()
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path, coin_flip=lambda: 1)
    orch.run_debate(dogs, cats, judge)
    for agent, side in [(dogs, "dogs"), (cats, "cats")]:
        briefs = [c for c in agent.receive.call_args_list if isinstance(c.args[0], OpeningBrief)]
        assert briefs and briefs[0].args[0].side == side
    judge_briefs = [c for c in judge.receive.call_args_list if isinstance(c.args[0], OpeningBrief)]
    assert judge_briefs and judge_briefs[0].args[0].rubric is not None


def test_raises_when_agent_returns_non_ping(tmp_path: Path):
    broken = mock_agent("dogs")
    broken.receive.side_effect = lambda env: None if isinstance(env, OpeningBrief) else "garbage"
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path, coin_flip=lambda: 1)
    with pytest.raises(RuntimeError, match="did not return a Ping"):
        orch.run_debate(broken, mock_agent("cats"), mock_judge())


def test_second_speaker_sees_opener_ping_as_previous(tmp_path: Path):
    """Second speaker receives the opener's fresh ping as `previous_ping` —
    the chain that makes clash possible in round 1."""
    orch = Orchestrator(topic="t", num_rounds=1, results_dir=tmp_path, coin_flip=lambda: 1)
    dogs, cats, judge = mock_agent("dogs"), mock_agent("cats"), mock_judge()
    orch.run_debate(dogs, cats, judge)
    cats_turn = [c for c in cats.receive.call_args_list if isinstance(c.args[0], YourTurn)][0]
    prev = cats_turn.args[0].previous_ping
    assert prev is not None and prev.side == "dogs" and prev.round == 1


def test_records_scores(tmp_path: Path):
    """Final DebateResult.scores mirrors what the judge accumulated."""
    orch = Orchestrator(topic="t", num_rounds=2, results_dir=tmp_path, coin_flip=lambda: 1)
    result = orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    assert isinstance(result.scores[0], Score)
    assert result.verdict.dogs_total == 20
    assert result.verdict.cats_total == 18
    assert result.verdict.winner == "dogs"
    Verdict.model_validate(result.verdict.model_dump())
