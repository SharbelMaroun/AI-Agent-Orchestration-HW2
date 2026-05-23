"""Pricing table + cost tracking. See docs/PRD_gatekeeper.md §5 + §9a.

Cache pricing follows Anthropic's published multipliers: writes cost 1.25× the
base input price, reads cost 0.10×. Other providers fall back to the plain
input/output prices because they don't expose cache token counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import ModelPrice

CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


def compute_cost(
    provider: str,
    model: str,
    pricing: dict[str, dict[str, ModelPrice]],
    input_tokens: int,
    output_tokens: int,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> float:
    """Return USD cost for one LLM call. Unknown provider/model → 0.0."""
    price = pricing.get(provider, {}).get(model)
    if price is None:
        return 0.0
    base_in = price.input_per_million_usd / 1_000_000
    base_out = price.output_per_million_usd / 1_000_000
    return (
        input_tokens * base_in
        + output_tokens * base_out
        + cache_creation * base_in * CACHE_WRITE_MULTIPLIER
        + cache_read * base_in * CACHE_READ_MULTIPLIER
    )


@dataclass
class CostTracker:
    """Per-model running totals for the cost report."""

    by_model: dict[str, dict] = field(default_factory=dict)
    total_usd: float = 0.0
    total_input_like: int = 0  # input + cache_creation + cache_read
    total_cache_read: int = 0

    def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation: int,
        cache_read: int,
        cost: float,
    ) -> None:
        key = f"{provider}/{model}"
        entry = self.by_model.setdefault(
            key,
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "cost_usd": 0.0,
            },
        )
        entry["input_tokens"] += input_tokens
        entry["output_tokens"] += output_tokens
        entry["cache_creation_tokens"] += cache_creation
        entry["cache_read_tokens"] += cache_read
        entry["cost_usd"] += cost
        self.total_usd += cost
        self.total_input_like += input_tokens + cache_creation + cache_read
        self.total_cache_read += cache_read

    def cache_read_pct(self) -> float:
        if self.total_input_like == 0:
            return 0.0
        return 100.0 * self.total_cache_read / self.total_input_like

    def summary(self) -> dict:
        return {
            "total_usd": self.total_usd,
            "by_model": {k: dict(v) for k, v in self.by_model.items()},
            "cache_read_pct": self.cache_read_pct(),
        }


def cost_report_from_pings(pings, models: dict, pricing: dict) -> dict:
    """Build a `cost_report` dict (same shape as `CostTracker.summary()`) from
    per-ping token counts. Used by the orchestrator when no gatekeeper-level
    cost tracking is wired in (default SDK uses passthrough). Skips pings
    whose side isn't in `models` or whose model isn't priced."""
    tracker = CostTracker()
    for ping in pings:
        model_ref = models.get(ping.side)
        if model_ref is None:
            continue
        provider, name = model_ref.provider, model_ref.name
        cost = compute_cost(provider, name, pricing, ping.tokens_in, ping.tokens_out)
        tracker.record(provider, name, ping.tokens_in, ping.tokens_out, 0, 0, cost)
    return tracker.summary()
