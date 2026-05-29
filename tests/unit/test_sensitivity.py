"""Unit tests for the OAT sensitivity engine (debate.services.analysis.sensitivity)."""

from __future__ import annotations

from debate.services.analysis.sensitivity import (
    _arc_elasticity,
    economics_evaluator,
    run_oat,
)
from debate.shared.config import ModelPrice, TokenModelCfg


def _linear_evaluator(params: dict) -> dict[str, float]:
    """metric = 10 * num_rounds; ignores the categorical 'mode' factor."""
    return {"m": 10.0 * float(params["num_rounds"])}


def _report():
    baseline = {"num_rounds": 10, "mode": "a"}
    factors = {"num_rounds": [5, 10, 15], "mode": ["a", "b"]}
    return run_oat(baseline=baseline, factors=factors, evaluate=_linear_evaluator, metric="m")


def test_baseline_metric_recorded() -> None:
    assert _report().baseline_metrics["m"] == 100.0


def test_tornado_sorted_by_range_desc() -> None:
    rep = _report()
    assert rep.factors[0].factor == "num_rounds"  # range 100
    assert rep.factors[-1].factor == "mode"  # range 0 (ignored)
    assert rep.factors[0].metric_range >= rep.factors[-1].metric_range


def test_numeric_factor_elasticity_is_linear() -> None:
    nr = next(f for f in _report().factors if f.factor == "num_rounds")
    assert abs(nr.elasticity - 1.0) < 1e-9  # 10*R is unit-elastic


def test_categorical_factor_elasticity_none() -> None:
    mode = next(f for f in _report().factors if f.factor == "mode")
    assert mode.elasticity is None
    assert mode.metric_range == 0.0


def test_sweep_points_cover_all_levels() -> None:
    nr = next(f for f in _report().factors if f.factor == "num_rounds")
    assert [p.level for p in nr.points] == [5, 10, 15]


def test_arc_elasticity_degenerate_cases() -> None:
    assert _arc_elasticity([(1.0, 2.0)], 1.0, 2.0) is None  # single point
    assert _arc_elasticity([("a", 1.0), ("b", 2.0)], "a", 1.0) is None  # categorical
    assert _arc_elasticity([(1.0, 1.0), (2.0, 2.0)], 1.0, 0.0) is None  # zero baseline metric
    assert _arc_elasticity([(2.0, 1.0), (2.0, 3.0)], 2.0, 1.0) is None  # zero factor spread


def test_economics_evaluator_returns_metric_keys() -> None:
    tm = TokenModelCfg(
        tokens_per_word=1.2,
        fixed_overhead_tokens=1000,
        history_factor=6.0,
        judge_overhead_ratio=0.8,
    )
    pricing = {
        "openai": {
            "gpt-4o-mini": ModelPrice(input_per_million_usd=0.15, output_per_million_usd=0.6)
        }
    }
    ev = economics_evaluator(tm, pricing)
    metrics = ev(
        {
            "num_rounds": 10,
            "max_words_per_ping": 250,
            "model": "openai/gpt-4o-mini",
            "cache_read_pct": 0.0,
        }
    )
    assert set(metrics) == {
        "cost_usd",
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "llm_calls",
    }
    assert metrics["cost_usd"] > 0
