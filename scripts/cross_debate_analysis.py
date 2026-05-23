"""Cross-debate analysis — produces PNGs in `assets/` from every
`results/debates/debate_*.json` on disk.

Run with: `uv run python scripts/cross_debate_analysis.py`

Chart implementations are split across three sibling helper modules so
this file (and each helper) stays under the 150-LOC cap (CLAUDE.md §4):
  _chart_overview.py  — win pie + margin bar
  _chart_personas.py  — per-dimension grouped bars + radar
  _chart_economy.py   — cumulative score, token+cost, citation density"""

from __future__ import annotations

import json
from pathlib import Path

from _chart_economy import citation_density, score_evolution, token_and_cost
from _chart_overview import margin_distribution, win_record
from _chart_personas import dimension_averages, per_dimension_radar

from debate.shared.schemas import DebateResult

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)
DEBATES = sorted((ROOT / "results" / "debates").glob("debate_*.json"))

results = [DebateResult.model_validate(json.loads(p.read_text(encoding="utf-8"))) for p in DEBATES]
print(f"Loaded {len(results)} debates.")

CHARTS = [
    ("win_record.png", win_record),
    ("margin_distribution.png", margin_distribution),
    ("dimension_averages.png", dimension_averages),
    ("per_dimension_radar.png", per_dimension_radar),
    ("score_evolution.png", score_evolution),
    ("token_and_cost.png", token_and_cost),
    ("citation_density.png", citation_density),
]

for filename, fn in CHARTS:
    fn(results, ASSETS / filename)
    print(f"  generated {filename}")

print("\nDone. PNGs in", ASSETS)
