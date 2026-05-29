# PRD — Parameter Sensitivity Analysis

**Version:** 1.00 · Parent: `docs/PRD.md` · Required by CLAUDE.md §12 + guidelines §9 ("parameter research, sensitivity analysis").
**Status:** Implemented. `DebateSDK.run_sensitivity_analysis()` + `DebateSDK.empirical_summary()` back a reproducible, zero-API-cost study; `scripts/sensitivity_analysis.py` regenerates the report JSON and four PNGs; results feed the analysis notebook.

---

## 1. Purpose
Quantify **how the debate's economics respond to its tunable parameters**, and how its *outcomes* vary across real runs — the systematic parameter research CLAUDE.md §12 requires. We answer: *which knob moves cost/tokens most, and by how much?*

## 2. Theoretical background
We combine two complementary methods:

- **One-At-a-Time (OAT) sensitivity.** Vary one factor across a level grid while holding the others at a baseline, and observe the target metric. OAT is the canonical screening design (Saltelli et al., 2008) — cheap, interpretable, and exact for a deterministic model.
- **Arc elasticity** (a discrete partial-derivative proxy). For a numeric factor `x` and metric `y`,
  $$\varepsilon \;=\; \frac{\Delta y / y_0}{\Delta x / x_0}$$
  measured over the swept range around baseline `(x_0, y_0)`. `ε ≈ 1` ⇒ linear response; `ε > 1` ⇒ super-linear (e.g. quadratic); `ε < 0` ⇒ inverse.
- **Variance-based importance.** Per factor we report the metric **range** (max − min over levels) and **coefficient of variation** `CV = σ/μ`. Factors are tornado-ranked by range — the standard tornado-diagram ordering.

The metric itself comes from a **calibrated analytical cost model** (see §5), so the sweep is deterministic and needs no LLM calls.

## 3. Interface (via SDK — the sole entry point)
```python
sdk.run_sensitivity_analysis(metric="cost_usd") -> SensitivityReport   # OAT sweep, tornado-ranked
sdk.empirical_summary() -> EmpiricalStats                              # distributions over recorded debates
```
Service layer (`debate.services.analysis`):
```python
predict_economics(*, num_rounds, max_words_per_ping, model, cache_read_pct,
                  token_model, pricing) -> DebateEconomics
run_oat(*, baseline, factors, evaluate, metric) -> SensitivityReport
economics_evaluator(token_model, pricing) -> Evaluator   # default params->metrics fn
empirical_summary(results_dir) -> EmpiricalStats
build_report(setup, metric) / save_report(report, out_dir, filename)
```

## 4. I/O spec
**Input (Setup):** `config/setup.json -> analysis` — `token_model` calibration, `baseline` operating point, and `factors` (the OAT level grids). **Input (data):** `results/debates/debate_*.json` for the empirical half.
**Output:** `SensitivityReport` (per-factor `points`, `elasticity`, `metric_range`, `metric_cv`, tornado-ranked) persisted to `results/sensitivity/sensitivity_{cost,tokens}.json`; `EmpiricalStats` (five-number summaries per metric + per rubric dimension); four PNGs in `assets/` (tornado, factor lines, rounds×words heatmap, empirical box plots).

## 5. Calibration (token model)
The analytical model is fitted to the 40 recorded debates:

| Constant | Value | Source |
|---|---|---|
| `tokens_per_word` | 1.21 | mean output 302 tok ÷ 250-word cap |
| `fixed_overhead_tokens` | 1136 | round-0 intercept of per-round input fit |
| `history_factor` | 6.05 | slope 1828 tok/round ÷ 302 tok/ping |
| `judge_overhead_ratio` | 0.78 | judge cost ÷ speaking cost at baseline |

Functional form: output is **linear** in `num_rounds` and `max_words_per_ping`; input is **quadratic** in `num_rounds` because each agent re-sends its accumulated history every round (input/call ≈ `fixed + history_factor·output·r`). The baseline prediction reproduces the **empirical mean cost ($0.0663)** exactly.

## 6. Headline findings
Tornado ranking of `cost_usd` (baseline R=10, W=250, gpt-4o-mini):

| Factor | Range (USD) | CV | Elasticity |
|---|---|---|---|
| model | 1.038 | 0.98 | — (categorical) |
| num_rounds | 0.115 | 0.55 | **+1.74** (super-linear) |
| max_words_per_ping | 0.072 | 0.46 | +0.91 (≈ linear) |
| cache_read_pct | 0.040 | 0.33 | — (negative, linear) |

**Model choice dominates** by an order of magnitude; among debate-shape knobs, `num_rounds` is most sensitive and its **+1.74 elasticity confirms the predicted quadratic cost growth**. Empirically (40 debates): dogs win 80%, margin μ=8.1 σ=5.7 (one 0 → tie-break fired), `structure`/`clash` saturate (σ≈0.2) while `pathos`/`ethos`/`logos` discriminate (σ≈0.5).

## 7. Alternatives considered
- **Live LLM OAT sweep** (run real debates per level). Rejected as the default: ~$1–3 + ~1–2 h per pass, non-reproducible by a grader without keys, and stochastic. The harness is evaluator-pluggable, so a live evaluator can be slotted in later without engine changes.
- **Variance-based Sobol indices.** More rigorous for interactions but needs hundreds–thousands of samples; overkill for four mostly-independent factors. The rounds×words **heatmap** captures the one interaction that matters.
- **Mining existing debates for parameter sensitivity.** Rejected — all 40 recorded debates ran at the same parameters (10 rounds, 250 words), so they reveal *output* variance (used for the empirical half) but cannot isolate parameter effects. Hence the calibrated analytical model.

## 8. Performance metrics
- Full report + 4 PNGs regenerate in **< 5 s**, **$0.00** API cost, fully deterministic (same inputs → identical JSON).
- Calibration accuracy: predicted baseline cost within **<0.1%** of the empirical mean.

## 9. Success criteria
- OAT sweep covers ≥ 4 factors with ≥ 3 levels each; tornado-ranked. ✅
- At least one numeric elasticity + one variance measure reported per factor. ✅
- ≥ 4 chart types (bar/tornado, line, heatmap, box). ✅
- Reproducible by a grader on a fresh clone with `uv run python scripts/sensitivity_analysis.py`. ✅

## 10. Test scenarios
- **Linearity:** output tokens double when rounds or words double. ✅ `test_cost_model`
- **Quadratic input:** `input(2R) > 2·input(R)`. ✅
- **Cache:** higher `cache_read_pct` lowers cost. ✅
- **Tornado order:** factors returned sorted by range desc. ✅ `test_sensitivity`
- **Elasticity:** unit-elastic synthetic model → ε≈1; categorical → `None`; degenerate (single level / zero spread / zero baseline) → `None`. ✅
- **Empirical:** aggregates win rate + five-number summaries; empty dir → zeroed stats. ✅ `test_empirical`
- **SDK + persistence:** `run_sensitivity_analysis` ranked; `build_report` raises without an `analysis` block; `save_report` round-trips JSON. ✅ `test_analysis_runner`
