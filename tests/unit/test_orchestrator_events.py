"""Orchestrator event-streaming tests: `on_event` callback fires for every
ping, every per-ping score, and the final verdict, in order.

Split off from `test_orchestrator.py` for the 150-LOC test cap."""

from __future__ import annotations

from pathlib import Path

from debate.services.orchestrator import Orchestrator
from debate.shared.schemas import DebateResult
from tests.unit._orchestrator_fixtures import mock_agent, mock_judge


def test_on_event_streams_pings_scores_and_verdict(tmp_path: Path):
    """Event order: announcement → (ping, score) × 4 → verdict (for 2 rounds)."""
    events: list[tuple[str, object]] = []
    orch = Orchestrator(
        topic="t",
        num_rounds=2,
        results_dir=tmp_path,
        on_event=lambda kind, payload: events.append((kind, payload)),
        coin_flip=lambda: 1,
    )
    orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    kinds = [k for k, _ in events]
    assert kinds.count("ping") == 4
    assert kinds.count("score") == 4
    assert kinds.count("verdict") == 1
    assert kinds.count("announcement") == 1
    assert kinds[-1] == "verdict"
    # Each ping is followed by its score for the same side.
    for i, (k, payload) in enumerate(events[:-1]):
        if k != "ping":
            continue
        nxt_kind, nxt_payload = events[i + 1]
        assert nxt_kind == "score"
        assert getattr(payload, "side", None) == getattr(nxt_payload, "side", None)


def test_on_event_none_is_noop(tmp_path: Path):
    """Default behavior (no callback) still produces a complete DebateResult."""
    orch = Orchestrator(
        topic="t",
        num_rounds=1,
        results_dir=tmp_path,
        on_event=None,
        coin_flip=lambda: 1,
    )
    result = orch.run_debate(mock_agent("dogs"), mock_agent("cats"), mock_judge())
    assert isinstance(result, DebateResult)
    assert len(result.pings) == 2
