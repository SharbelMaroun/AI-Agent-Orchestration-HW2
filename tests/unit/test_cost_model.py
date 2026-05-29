"""Unit tests for the analytical cost model (debate.services.analysis.cost_model)."""

from __future__ import annotations

from debate.services.analysis.cost_model import DebateEconomics, predict_economics
from debate.shared.config import ModelPrice, TokenModelCfg


def _tm() -> TokenModelCfg:
    return TokenModelCfg(
        tokens_per_word=1.2,
        fixed_overhead_tokens=1000,
        history_factor=6.0,
        judge_overhead_ratio=0.8,
    )


def _pricing() -> dict:
    return {
        "openai": {
            "gpt-4o-mini": ModelPrice(input_per_million_usd=0.15, output_per_million_usd=0.60)
        }
    }


def _predict(num_rounds: int = 10, max_words: int = 250, cache: float = 0.0) -> DebateEconomics:
    return predict_economics(
        num_rounds=num_rounds,
        max_words_per_ping=max_words,
        model="openai/gpt-4o-mini",
        cache_read_pct=cache,
        token_model=_tm(),
        pricing=_pricing(),
    )


def test_output_tokens_linear_in_rounds() -> None:
    assert _predict(num_rounds=20).output_tokens == 2 * _predict(num_rounds=10).output_tokens


def test_output_tokens_linear_in_words() -> None:
    assert _predict(max_words=500).output_tokens == 2 * _predict(max_words=250).output_tokens


def test_input_tokens_superlinear_in_rounds() -> None:
    # History re-send makes input grow quadratically: input(2R) > 2 * input(R).
    assert _predict(num_rounds=20).input_tokens > 2 * _predict(num_rounds=10).input_tokens


def test_llm_calls_formula() -> None:
    assert _predict(num_rounds=10).llm_calls == 41  # 4R + 1
    assert _predict(num_rounds=5).llm_calls == 21


def test_total_tokens_is_sum() -> None:
    e = _predict()
    assert e.total_tokens == e.input_tokens + e.output_tokens


def test_cache_reduces_cost() -> None:
    assert _predict(cache=0.5).cost_usd < _predict(cache=0.0).cost_usd


def test_unknown_model_costs_zero() -> None:
    e = predict_economics(
        num_rounds=10,
        max_words_per_ping=250,
        model="acme/unpriced",
        cache_read_pct=0.0,
        token_model=_tm(),
        pricing=_pricing(),
    )
    assert e.cost_usd == 0.0
    assert e.total_tokens > 0  # tokens still predicted even when unpriced


def test_cost_positive_for_priced_model() -> None:
    assert _predict().cost_usd > 0.0
