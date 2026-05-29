"""Result dataclasses for the sensitivity analysis (the engine's Output).

Kept separate from ``sensitivity.py`` so each file stays a single concern and
under the 150-LOC cap. All fields are JSON-serialisable via
``dataclasses.asdict`` for persistence to results/sensitivity/.
"""

from __future__ import annotations

from dataclasses import dataclass

Level = int | float | str


@dataclass(frozen=True)
class SweepPoint:
    """One evaluated point of an OAT sweep: a factor level and its metrics."""

    level: Level
    metrics: dict[str, float]


@dataclass(frozen=True)
class FactorSensitivity:
    """How one factor moves the target metric across its swept levels.

    ``elasticity`` is the dimensionless arc-elasticity over the numeric range
    (% change in metric per % change in factor); ``None`` for categorical
    factors (e.g. model choice). ``metric_range`` and ``metric_cv`` are the
    variance-based importance measures used for the tornado ranking.
    """

    factor: str
    metric: str
    baseline_value: float
    points: list[SweepPoint]
    elasticity: float | None
    metric_range: float
    metric_cv: float


@dataclass(frozen=True)
class SensitivityReport:
    """Full OAT report for one target metric, factors tornado-ranked."""

    metric: str
    baseline: dict[str, Level]
    baseline_metrics: dict[str, float]
    factors: list[FactorSensitivity]
