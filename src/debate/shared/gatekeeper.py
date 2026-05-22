"""ApiGatekeeper — single chokepoint for all external API calls.

See docs/PRD_gatekeeper.md. Every LLM/search/embedding call in the project
flows through `ApiGatekeeper.execute(...)`: rate limits per service, FIFO
backpressure, retries with backoff, token+cost recording, budget alerts.

Internals (rolling windows, per-service state, retry classifier, exceptions,
QueueStatus) live in `rate_limiter.py` to keep this file under the 150-LOC cap.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from .config import RateLimitConfig, SetupConfig
from .logger import log_cost_entry
from .pricing import CostTracker, compute_cost
from .rate_limiter import (
    ApiCallFailedError,
    BudgetExceededError,
    QueueFullError,
    QueueStatus,
    ServiceState,
    is_retryable,
)
from .schemas import CompletionResponse

__all__ = ["ApiCallFailedError", "ApiGatekeeper", "BudgetExceededError",
           "QueueFullError", "QueueStatus"]


class ApiGatekeeper:
    """Centralized API call manager. See docs/PRD_gatekeeper.md."""

    def __init__(
        self,
        rate_config: RateLimitConfig,
        setup: SetupConfig,
        logger: logging.Logger,
        cost_logger: logging.Logger | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.rate_config = rate_config
        self.setup = setup
        self.logger = logger
        self.cost_logger = cost_logger
        self._sleep = sleep_fn
        self.tracker = CostTracker()
        self._services: dict[str, ServiceState] = {
            name: ServiceState(lim) for name, lim in rate_config.services.items()
        }
        self._budget_lock = threading.Lock()
        self._warned = False

    def _state(self, service: str) -> ServiceState:
        return self._services.get(service) or self._services["default"]

    def _wait_for_slot(self, st: ServiceState) -> None:
        with st.lock:
            if st.pending >= st.limit.queue_max_depth:
                raise QueueFullError(f"queue at {st.limit.queue_max_depth}")
            st.pending += 1
        try:
            while True:
                with st.lock:
                    now = time.monotonic()
                    st.minute.prune(now, 60.0)
                    st.hour.prune(now, 3600.0)
                    if (
                        len(st.minute) < st.limit.requests_per_minute
                        and len(st.hour) < st.limit.requests_per_hour
                    ):
                        st.minute.add(now)
                        st.hour.add(now)
                        return
                self._sleep(0.05)
        finally:
            with st.lock:
                st.pending -= 1

    def execute(
        self, api_call: Callable[..., Any], *args: Any, service: str = "default", **kwargs: Any
    ) -> Any:
        st = self._state(service)
        self._wait_for_slot(st)
        last_exc: BaseException | None = None
        with st.semaphore:
            with st.lock:
                st.in_flight += 1
            try:
                for attempt in range(1, st.limit.max_retries + 2):
                    try:
                        result = api_call(*args, **kwargs)
                    except Exception as e:
                        last_exc = e
                        if not is_retryable(e, st.limit.retryable_status_codes):
                            raise
                        if attempt > st.limit.max_retries:
                            break
                        self.logger.warning(
                            "retry attempt=%d service=%s err=%s", attempt, service, e
                        )
                        self._sleep(st.limit.retry_after_seconds * attempt)
                        continue
                    self._record(result)
                    return result
                raise ApiCallFailedError(f"exhausted retries: {last_exc}") from last_exc
            finally:
                with st.lock:
                    st.in_flight -= 1

    def _record(self, result: Any) -> None:
        if not isinstance(result, CompletionResponse):
            return
        cost = compute_cost(
            result.provider, result.model, self.setup.pricing,
            result.input_tokens, result.output_tokens,
            result.cache_creation_tokens, result.cache_read_tokens,
        )
        self.tracker.record(
            result.provider, result.model,
            result.input_tokens, result.output_tokens,
            result.cache_creation_tokens, result.cache_read_tokens, cost,
        )
        if self.cost_logger is not None:
            log_cost_entry(self.cost_logger, {
                "provider": result.provider, "model": result.model,
                "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                "cache_creation": result.cache_creation_tokens,
                "cache_read": result.cache_read_tokens, "cost_usd": cost,
            })
        self._check_budget()

    def _check_budget(self) -> None:
        budget = self.setup.budget_usd
        if budget <= 0:
            return
        ratio = self.tracker.total_usd / budget
        warn = self.rate_config.budget.warning_threshold_pct / 100
        hard = self.rate_config.budget.hard_limit_pct / 100
        with self._budget_lock:
            if ratio >= hard:
                self.logger.error(
                    "budget exceeded: $%.4f of $%.2f", self.tracker.total_usd, budget
                )
                raise BudgetExceededError(
                    f"spent ${self.tracker.total_usd:.4f} of ${budget:.2f}"
                )
            if ratio >= warn and not self._warned:
                self._warned = True
                self.logger.warning("budget at %.1f%% of $%.2f", ratio * 100, budget)

    def get_queue_status(self, service: str = "default") -> QueueStatus:
        st = self._state(service)
        with st.lock:
            return QueueStatus(service, st.pending, st.in_flight,
                               len(st.minute), len(st.hour))

    def get_token_summary(self) -> dict:
        return self.tracker.summary()
