"""Reproducible, zero-cost sensitivity analysis over debate economics.

See docs/PRD_sensitivity.md. Combines a calibrated analytical cost model
(OAT parameter sweeps) with empirical distributions mined from recorded
debates. Public API below; the SDK exposes ``run_sensitivity_analysis`` and
``empirical_summary`` on top of these.
"""

from debate.services.analysis._models import (
    FactorSensitivity,
    SensitivityReport,
    SweepPoint,
)
from debate.services.analysis.cost_model import DebateEconomics, predict_economics
from debate.services.analysis.empirical import (
    Distribution,
    EmpiricalStats,
    empirical_summary,
    load_results,
)
from debate.services.analysis.runner import build_report, save_report
from debate.services.analysis.sensitivity import economics_evaluator, run_oat
from debate.shared.version import __version__

__all__ = [
    "DebateEconomics",
    "Distribution",
    "EmpiricalStats",
    "FactorSensitivity",
    "SensitivityReport",
    "SweepPoint",
    "build_report",
    "economics_evaluator",
    "empirical_summary",
    "load_results",
    "predict_economics",
    "run_oat",
    "save_report",
    "__version__",
]
