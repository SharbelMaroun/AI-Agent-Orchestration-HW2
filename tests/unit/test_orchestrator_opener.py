"""Coin-flip opener + Judge announcement tests.

Split off from `test_orchestrator.py` for the 150-LOC test cap (CLAUDE.md §6).
Pins the per-debate coin-flip behavior (`1 → Dogs opens, 0 → Cats opens`)
and the templated `announcement` event fired before round 1."""

from __future__ import annotations

from pathlib import Path

from debate.services.orchestrator import Orchestrator
from debate.shared.schemas import YourTurn
from tests.unit._orchestrator_fixtures import mock_agent, mock_judge


def test_opener_decided_by_coin_flip_dogs(tmp_path: Path):
    """Coin flip returning 1 makes Dogs the opener of round 1."""
    orch = Orchestrator(
        topic="t",
        num_rounds=1,
        results_dir=tmp_path,
        coin_flip=lambda: 1,
    )
    dogs, cats, judge = mock_agent("dogs"), mock_agent("cats"), mock_judge()
    orch.run_debate(dogs, cats, judge)
    your_turn_calls = [c for c in dogs.receive.call_args_list if isinstance(c.args[0], YourTurn)]
    first = your_turn_calls[0].args[0]
    assert first.round == 1
    assert first.previous_ping is None


def test_opener_decided_by_coin_flip_cats(tmp_path: Path):
    """Coin flip returning 0 makes Cats the opener of round 1."""
    orch = Orchestrator(
        topic="t",
        num_rounds=1,
        results_dir=tmp_path,
        coin_flip=lambda: 0,
    )
    dogs, cats, judge = mock_agent("dogs"), mock_agent("cats"), mock_judge()
    orch.run_debate(dogs, cats, judge)
    your_turn_calls = [c for c in cats.receive.call_args_list if isinstance(c.args[0], YourTurn)]
    first = your_turn_calls[0].args[0]
    assert first.round == 1
    assert first.previous_ping is None


def test_emits_announcement_before_round_1(tmp_path: Path):
    """The orchestrator fires an `announcement` event (Judge welcomes both
    sides and reveals the coin-flip result) BEFORE the first ping."""
    events: list[tuple[str, object]] = []
    orch = Orchestrator(
        topic="t",
        num_rounds=1,
        results_dir=tmp_path,
        on_event=lambda k, p: events.append((k, p)),
        coin_flip=lambda: 1,
    )
    orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    kinds = [k for k, _ in events]
    assert kinds[0] == "announcement"
    assert "DOGS will open" in events[0][1]


def test_announcement_text_includes_topic_and_rules(tmp_path: Path):
    events: list[tuple[str, object]] = []
    orch = Orchestrator(
        topic="Are cats or dogs better?",
        num_rounds=10,
        rules="be brief",
        results_dir=tmp_path,
        on_event=lambda k, p: events.append((k, p)),
        coin_flip=lambda: 0,
    )
    orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    text = events[0][1]
    assert "Are cats or dogs better?" in text
    assert "be brief" in text
    assert "10 round" in text
    assert "CATS will open" in text
