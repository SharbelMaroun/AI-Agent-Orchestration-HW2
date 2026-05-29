"""Empirical analysis over recorded debates — the real-data half of the study.

Loads every ``results/debates/debate_*.json``, computes per-debate outcome
metrics and per-dimension judge-score distributions, and returns summary
statistics (mean / std / quartiles) for variance reporting and box plots. This
complements the analytical sensitivity model with the *observed* output
variance at the fixed shipped parameters (the analytical model predicts means;
real LLM runs reveal the spread).
"""

from __future__ import annotations

import json
import statistics as st
from dataclasses import dataclass
from pathlib import Path

from debate.shared.schemas import DebateResult

DIMENSIONS = ("structure", "logos", "pathos", "ethos", "clash")


@dataclass(frozen=True)
class Distribution:
    """Five-number summary + mean/std of one observed series (for box plots)."""

    name: str
    n: int
    mean: float
    std: float
    minimum: float
    q1: float
    median: float
    q3: float
    maximum: float


@dataclass(frozen=True)
class EmpiricalStats:
    """Aggregate stats across all recorded debates."""

    n_debates: int
    metrics: dict[str, Distribution]  # margin, dogs_total, cats_total, cost_usd, total_tokens
    dimensions: dict[str, Distribution]  # per-rubric-dimension score over all pings
    dogs_win_rate: float


def _distribution(name: str, values: list[float]) -> Distribution:
    """Five-number summary; degenerate-safe for empty / single-value series."""
    if not values:
        return Distribution(name, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    vals = sorted(float(v) for v in values)
    n = len(vals)
    std = st.pstdev(vals) if n > 1 else 0.0
    if n >= 2:
        q1, median, q3 = st.quantiles(vals, n=4)
    else:
        q1 = median = q3 = vals[0]
    return Distribution(name, n, st.mean(vals), std, vals[0], q1, median, q3, vals[-1])


def _debate_tokens(result: DebateResult) -> float:
    """Total input+output tokens recorded for one debate's cost report."""
    by_model = (result.cost_report or {}).get("by_model") or {}
    return float(
        sum(m.get("input_tokens", 0) + m.get("output_tokens", 0) for m in by_model.values())
    )


def load_results(results_dir: str | Path = "results/debates") -> list[DebateResult]:
    """Parse every ``debate_*.json`` under ``results_dir`` into DebateResults."""
    root = Path(results_dir)
    if not root.exists():
        return []
    return [
        DebateResult.model_validate(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(root.glob("debate_*.json"))
    ]


def empirical_summary(results_dir: str | Path = "results/debates") -> EmpiricalStats:
    """Summarise outcome + score distributions across all recorded debates."""
    results = load_results(results_dir)
    if not results:
        return EmpiricalStats(0, {}, {}, 0.0)
    verdicts = [r.verdict for r in results]
    metrics = {
        "margin": _distribution("margin", [v.margin for v in verdicts]),
        "dogs_total": _distribution("dogs_total", [v.dogs_total for v in verdicts]),
        "cats_total": _distribution("cats_total", [v.cats_total for v in verdicts]),
        "cost_usd": _distribution(
            "cost_usd", [float((r.cost_report or {}).get("total_usd", 0.0)) for r in results]
        ),
        "total_tokens": _distribution("total_tokens", [_debate_tokens(r) for r in results]),
    }
    dimensions = {
        dim: _distribution(dim, [getattr(s, dim) for r in results for s in r.scores])
        for dim in DIMENSIONS
    }
    dogs_win_rate = sum(1 for v in verdicts if v.winner == "dogs") / len(verdicts)
    return EmpiricalStats(len(results), metrics, dimensions, dogs_win_rate)
