"""Cost recording + budget enforcement.

Extracted from `gatekeeper.py` to keep that file under the 150-LOC cap.
The recorder owns the per-call cost math, the JSONL persistence, and the
two-threshold budget check (WARNING at warn_pct, raise at hard_pct).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from .config import RateLimitConfig, SetupConfig
from .logger import log_cost_entry
from .pricing import CostTracker, compute_cost
from .rate_limiter import BudgetExceededError
from .schemas import CompletionResponse


class CostRecorder:
    """Records token cost from `CompletionResponse`s and enforces budget."""

    def __init__(
        self,
        setup: SetupConfig,
        rate_config: RateLimitConfig,
        logger: logging.Logger,
        cost_logger: logging.Logger | None = None,
    ) -> None:
        self.setup = setup
        self.rate_config = rate_config
        self.logger = logger
        self.cost_logger = cost_logger
        self.tracker = CostTracker()
        self._lock = threading.Lock()
        self._warned = False

    def record(self, result: Any) -> None:
        """Tally token cost for a `CompletionResponse`; no-op for other types."""
        if not isinstance(result, CompletionResponse):
            return
        cost = compute_cost(
            result.provider,
            result.model,
            self.setup.pricing,
            result.input_tokens,
            result.output_tokens,
            result.cache_creation_tokens,
            result.cache_read_tokens,
        )
        self.tracker.record(
            result.provider,
            result.model,
            result.input_tokens,
            result.output_tokens,
            result.cache_creation_tokens,
            result.cache_read_tokens,
            cost,
        )
        if self.cost_logger is not None:
            log_cost_entry(
                self.cost_logger,
                {
                    "provider": result.provider,
                    "model": result.model,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cache_creation": result.cache_creation_tokens,
                    "cache_read": result.cache_read_tokens,
                    "cost_usd": cost,
                },
            )
        self._check_budget()

    def _check_budget(self) -> None:
        budget = self.setup.budget_usd
        if budget <= 0:
            return
        ratio = self.tracker.total_usd / budget
        warn = self.rate_config.budget.warning_threshold_pct / 100
        hard = self.rate_config.budget.hard_limit_pct / 100
        with self._lock:
            if ratio >= hard:
                self.logger.error("budget exceeded: $%.4f of $%.2f", self.tracker.total_usd, budget)
                raise BudgetExceededError(f"spent ${self.tracker.total_usd:.4f} of ${budget:.2f}")
            if ratio >= warn and not self._warned:
                self._warned = True
                self.logger.warning("budget at %.1f%% of $%.2f", ratio * 100, budget)

    def summary(self) -> dict:
        return self.tracker.summary()
