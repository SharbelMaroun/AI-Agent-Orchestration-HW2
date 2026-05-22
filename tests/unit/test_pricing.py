"""Unit tests for debate.shared.pricing."""

from __future__ import annotations

from debate.shared.config import ModelPrice
from debate.shared.pricing import (
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    CostTracker,
    compute_cost,
)


def _pricing() -> dict:
    return {
        "anthropic": {
            "claude-haiku": ModelPrice(input_per_million_usd=1.0, output_per_million_usd=4.0),
        }
    }


def test_compute_cost_input_output() -> None:
    cost = compute_cost("anthropic", "claude-haiku", _pricing(), 1_000_000, 1_000_000)
    assert cost == 5.0  # 1.0 + 4.0


def test_compute_cost_cache_tokens_use_multipliers() -> None:
    cost = compute_cost(
        "anthropic",
        "claude-haiku",
        _pricing(),
        input_tokens=0,
        output_tokens=0,
        cache_creation=1_000_000,
        cache_read=1_000_000,
    )
    expected = 1.0 * CACHE_WRITE_MULTIPLIER + 1.0 * CACHE_READ_MULTIPLIER
    assert abs(cost - expected) < 1e-9


def test_compute_cost_unknown_model_zero() -> None:
    assert compute_cost("anthropic", "ghost", _pricing(), 100, 100) == 0.0
    assert compute_cost("ghost", "claude-haiku", _pricing(), 100, 100) == 0.0


def test_tracker_aggregates_by_model() -> None:
    t = CostTracker()
    t.record("anthropic", "haiku", 100, 50, 0, 0, 0.001)
    t.record("anthropic", "haiku", 200, 75, 0, 0, 0.002)
    summary = t.summary()
    assert abs(summary["total_usd"] - 0.003) < 1e-9
    entry = summary["by_model"]["anthropic/haiku"]
    assert entry["input_tokens"] == 300
    assert entry["output_tokens"] == 125


def test_tracker_cache_read_pct() -> None:
    t = CostTracker()
    t.record("anthropic", "haiku", 100, 0, 0, 100, 0.001)
    # 100 input_like = 0 input + 0 creation + 100 read → wrong, recompute
    # actually input_like = 100 + 0 + 100 = 200, cache_read = 100 → 50%
    assert abs(t.cache_read_pct() - 50.0) < 1e-9


def test_tracker_empty_returns_zero_pct() -> None:
    assert CostTracker().cache_read_pct() == 0.0
