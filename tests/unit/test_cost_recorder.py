"""Unit tests for debate.shared.cost_recorder.CostRecorder.

Direct tests for the cost-recording logic that the gatekeeper composes.
The integration through the gatekeeper is covered by
`test_gatekeeper_budget_and_queue.py`; these tests pin the unit's
contract in isolation."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from debate.shared.cost_recorder import CostRecorder
from debate.shared.rate_limiter import BudgetExceededError
from debate.shared.schemas import CompletionResponse
from tests.unit._gatekeeper_fixtures import rate_cfg, setup_cfg


def _resp(in_tok: int = 100, out_tok: int = 50) -> CompletionResponse:
    return CompletionResponse(
        text="hi",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        model="haiku",
        provider="anthropic",
    )


def _recorder(
    budget: float = 5.0, warn: int = 80, hard: int = 100, cost_logger=None
) -> CostRecorder:
    return CostRecorder(
        setup=setup_cfg(budget),
        rate_config=rate_cfg(warn=warn, hard=hard),
        logger=logging.getLogger("test"),
        cost_logger=cost_logger,
    )


def test_record_completion_updates_tracker() -> None:
    r = _recorder(budget=1000)
    r.record(_resp(in_tok=1_000_000, out_tok=1_000_000))
    summary = r.summary()
    entry = summary["by_model"]["anthropic/haiku"]
    assert entry["input_tokens"] == 1_000_000
    assert entry["output_tokens"] == 1_000_000
    assert abs(summary["total_usd"] - 5.0) < 1e-9


def test_record_ignores_non_completion() -> None:
    r = _recorder()
    r.record({"some": "dict"})
    assert r.summary()["total_usd"] == 0.0


def test_budget_exceeded_raises() -> None:
    r = _recorder(budget=0.001)
    with pytest.raises(BudgetExceededError):
        r.record(_resp(in_tok=1_000_000, out_tok=1_000_000))


def test_budget_warning_fires_once(caplog) -> None:
    r = _recorder(budget=1.0, warn=1, hard=100)
    with caplog.at_level(logging.WARNING, logger="test"):
        r.record(_resp(in_tok=10_000, out_tok=10_000))
        r.record(_resp(in_tok=10_000, out_tok=10_000))
    warnings = [rec for rec in caplog.records if "budget at" in rec.getMessage()]
    assert len(warnings) == 1


def test_cost_logger_invoked_when_provided() -> None:
    cost_log = MagicMock()
    r = _recorder(cost_logger=cost_log)
    r.record(_resp())
    assert cost_log.info.called


def test_summary_matches_cost_tracker_shape() -> None:
    r = _recorder()
    r.record(_resp())
    s = r.summary()
    assert "total_usd" in s and "by_model" in s and "cache_read_pct" in s
