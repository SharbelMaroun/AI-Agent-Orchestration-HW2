"""Sensitivity-analysis runner — reproducible, zero API cost.

Run with: ``uv run python scripts/sensitivity_analysis.py``

Drives the SDK to (1) run the One-At-a-Time parameter sweep defined in
``config/setup.json -> analysis`` for cost and token metrics, persisting the
tornado-ranked reports to ``results/sensitivity/``; and (2) summarise the
observed score/outcome distributions across every recorded debate. Then emits
four PNGs into ``assets/``: tornado, per-factor response lines, a rounds×words
cost heatmap, and empirical rubric box plots. See docs/PRD_sensitivity.md.
"""

from __future__ import annotations

from pathlib import Path

from _chart_sensitivity import (
    empirical_boxplots,
    factor_lines,
    interaction_heatmap,
    tornado,
)

from debate.sdk.sdk import DebateSDK
from debate.services.analysis import save_report

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
SENS_DIR = ROOT / "results" / "sensitivity"

sdk = DebateSDK()

cost_report = sdk.run_sensitivity_analysis("cost_usd")
token_report = sdk.run_sensitivity_analysis("total_tokens")
save_report(cost_report, SENS_DIR, "sensitivity_cost.json")
save_report(token_report, SENS_DIR, "sensitivity_tokens.json")
print(f"Saved OAT reports to {SENS_DIR}")
print("Tornado ranking (cost_usd):")
for f in cost_report.factors:
    el = f"{f.elasticity:+.2f}" if f.elasticity is not None else " n/a"
    print(f"  {f.factor:20s} range={f.metric_range:.4g}  cv={f.metric_cv:.3f}  elasticity={el}")

stats = sdk.empirical_summary()
print(f"Empirical: {stats.n_debates} debates, dogs win rate {stats.dogs_win_rate:.0%}")

tornado(cost_report, ASSETS / "sensitivity_tornado.png")
factor_lines(cost_report, ASSETS / "sensitivity_factor_lines.png")
interaction_heatmap(sdk.setup, ASSETS / "sensitivity_heatmap.png")
empirical_boxplots(stats, ASSETS / "empirical_boxplots.png")
print(f"Generated 4 PNGs in {ASSETS}")
