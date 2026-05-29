"""Calibrated analytical cost/economics model for a debate run.

Predicts input/output tokens, USD cost, and LLM-call count for a debate of
``num_rounds`` rounds with ``max_words_per_ping`` words per ping, on a given
priced model, at a given cache-read fraction — *without* running an LLM. The
sensitivity engine (docs/PRD_sensitivity.md) uses it for reproducible,
zero-cost parameter research.

Functional form (the headline sensitivity result):
  * output tokens grow **linearly** with both ``num_rounds`` and
    ``max_words_per_ping``;
  * input tokens grow **quadratically** with ``num_rounds``, because every
    round each agent re-sends its accumulated history (history grows by
    ``history_factor`` x the ping output). Cost is therefore ~quadratic in
    ``num_rounds`` — the dominant sensitivity, matching the per-round token
    growth recorded in results/debates/.

The calibration constants live in config/setup.json -> ``analysis.token_model``
(fitted from recorded debates), never hardcoded here.
"""

from __future__ import annotations

from dataclasses import dataclass

from debate.shared.config import ModelPrice, TokenModelCfg
from debate.shared.pricing import compute_cost


@dataclass(frozen=True)
class DebateEconomics:
    """Predicted resource use for one debate (the cost model's Output)."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    llm_calls: int
    cost_usd: float


def _speaking_tokens(
    num_rounds: int, max_words_per_ping: int, tm: TokenModelCfg
) -> tuple[int, int]:
    """Return (input, output) tokens for the two speaking agents only.

    Per-call input = ``fixed_overhead + growth * r`` for round ``r`` (the
    affine history-accumulation fit); summed over R rounds this is quadratic.
    """
    output_per_ping = tm.tokens_per_word * max_words_per_ping
    growth = tm.history_factor * output_per_ping
    # 2 sides; sum_{r=1..R} (fixed + growth*r) = R*fixed + growth*R*(R+1)/2
    rounds_triangular = num_rounds * (num_rounds + 1) / 2
    speaking_input = 2 * (num_rounds * tm.fixed_overhead_tokens + growth * rounds_triangular)
    speaking_output = 2 * num_rounds * output_per_ping
    return round(speaking_input), round(speaking_output)


def predict_economics(
    *,
    num_rounds: int,
    max_words_per_ping: int,
    model: str,
    cache_read_pct: float,
    token_model: TokenModelCfg,
    pricing: dict[str, dict[str, ModelPrice]],
) -> DebateEconomics:
    """Predict one debate's economics. ``model`` is ``"provider/name"``.

    The judge's tokens are approximated as ``judge_overhead_ratio`` x the
    speaking tokens (same model/price as the speakers in the shipped config),
    which reproduces the recorded baseline cost. ``cache_read_pct`` of the
    input is billed at the cache-read multiplier via the shared pricing model.
    """
    provider, _, name = model.partition("/")
    s_in, s_out = _speaking_tokens(num_rounds, max_words_per_ping, token_model)
    total_input = round(s_in * (1 + token_model.judge_overhead_ratio))
    total_output = round(s_out * (1 + token_model.judge_overhead_ratio))
    cached = round(total_input * cache_read_pct)
    fresh_input = total_input - cached
    cost = compute_cost(provider, name, pricing, fresh_input, total_output, 0, cached)
    return DebateEconomics(
        input_tokens=total_input,
        output_tokens=total_output,
        total_tokens=total_input + total_output,
        llm_calls=4 * num_rounds + 1,  # 2R speaking + 2R judge scores + 1 verdict
        cost_usd=cost,
    )
