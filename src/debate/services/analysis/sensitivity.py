"""One-At-a-Time (OAT) sensitivity engine + importance indices.

Given a baseline operating point and a grid of levels per factor, vary ONE
factor at a time (holding the rest at baseline), evaluate a target metric, and
quantify each factor's influence three ways (docs/PRD_sensitivity.md §Method):

  * **arc elasticity** — % change in metric per % change in factor over the
    swept range (a discrete partial-derivative proxy); ``None`` for
    categorical factors such as model choice;
  * **range** — max-min of the metric across the factor's levels;
  * **coefficient of variation** — std/mean of the metric across the levels.

Factors are returned tornado-ranked by ``metric_range``. The evaluator is
injected (dependency injection) so the same engine works over the analytical
cost model or any other ``params -> metrics`` function.
"""

from __future__ import annotations

from collections.abc import Callable

from debate.shared.config import ModelPrice, TokenModelCfg

from ._models import FactorSensitivity, Level, SensitivityReport, SweepPoint
from .cost_model import predict_economics

Evaluator = Callable[[dict[str, Level]], dict[str, float]]


def economics_evaluator(
    token_model: TokenModelCfg,
    pricing: dict[str, dict[str, ModelPrice]],
) -> Evaluator:
    """Build the default evaluator: a debate-params dict -> metrics dict,
    backed by the calibrated analytical cost model (zero API cost)."""

    def _evaluate(params: dict[str, Level]) -> dict[str, float]:
        econ = predict_economics(
            num_rounds=int(params["num_rounds"]),
            max_words_per_ping=int(params["max_words_per_ping"]),
            model=str(params["model"]),
            cache_read_pct=float(params["cache_read_pct"]),
            token_model=token_model,
            pricing=pricing,
        )
        return {
            "cost_usd": econ.cost_usd,
            "total_tokens": float(econ.total_tokens),
            "input_tokens": float(econ.input_tokens),
            "output_tokens": float(econ.output_tokens),
            "llm_calls": float(econ.llm_calls),
        }

    return _evaluate


def _arc_elasticity(pairs: list[tuple[Level, float]], base_x: Level, base_y: float) -> float | None:
    """Elasticity over the numeric range; None if non-numeric or degenerate."""
    numeric = [(x, y) for x, y in pairs if isinstance(x, int | float) and not isinstance(x, bool)]
    if len(numeric) < 2 or not isinstance(base_x, int | float) or base_x == 0 or base_y == 0:
        return None
    lo = min(numeric, key=lambda t: t[0])
    hi = max(numeric, key=lambda t: t[0])
    dx = hi[0] - lo[0]
    if dx == 0:
        return None
    return ((hi[1] - lo[1]) / base_y) / (dx / base_x)


def _summarize(
    factor: str, metric: str, base_x: Level, base_y: float, points: list[SweepPoint]
) -> FactorSensitivity:
    vals = [p.metrics[metric] for p in points]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    cv = (var**0.5) / mean if mean else 0.0
    pairs = [(p.level, p.metrics[metric]) for p in points]
    return FactorSensitivity(
        factor=factor,
        metric=metric,
        baseline_value=base_y,
        points=points,
        elasticity=_arc_elasticity(pairs, base_x, base_y),
        metric_range=max(vals) - min(vals),
        metric_cv=cv,
    )


def run_oat(
    *,
    baseline: dict[str, Level],
    factors: dict[str, list[Level]],
    evaluate: Evaluator,
    metric: str,
) -> SensitivityReport:
    """Run the OAT sweep and return a tornado-ranked sensitivity report."""
    base_metrics = evaluate(baseline)
    base_y = base_metrics[metric]
    summaries: list[FactorSensitivity] = []
    for name, levels in factors.items():
        points = [SweepPoint(lvl, evaluate({**baseline, name: lvl})) for lvl in levels]
        summaries.append(_summarize(name, metric, baseline[name], base_y, points))
    summaries.sort(key=lambda f: f.metric_range, reverse=True)
    return SensitivityReport(metric, dict(baseline), base_metrics, summaries)
