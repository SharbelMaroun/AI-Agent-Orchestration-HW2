"""ApiGatekeeper — single chokepoint for all external API calls.

See docs/PRD_gatekeeper.md. Every LLM/search/embedding call in the project
flows through `ApiGatekeeper.execute(...)`: rate limits per service, FIFO
backpressure, retries with backoff, token+cost recording, budget alerts.

Internals split across sibling modules to keep this file under the 150-LOC
cap: rolling-window + service-state in `rate_limiter.py`, cost recording +
budget enforcement in `cost_recorder.py`, pricing math in `pricing.py`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from .config import RateLimitConfig, SetupConfig
from .cost_recorder import CostRecorder
from .middleware import Middleware, compose
from .rate_limiter import (
    ApiCallFailedError,
    BudgetExceededError,
    QueueFullError,
    QueueStatus,
    ServiceState,
    is_retryable,
)

__all__ = [
    "ApiCallFailedError",
    "ApiGatekeeper",
    "BudgetExceededError",
    "Middleware",
    "QueueFullError",
    "QueueStatus",
]


class ApiGatekeeper:
    """Centralized API call manager. See docs/PRD_gatekeeper.md."""

    def __init__(
        self,
        rate_config: RateLimitConfig,
        setup: SetupConfig,
        logger: logging.Logger,
        cost_logger: logging.Logger | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        middlewares: list[Middleware] | None = None,
    ) -> None:
        self.rate_config = rate_config
        self.setup = setup
        self.logger = logger
        self._sleep = sleep_fn
        # Cross-cutting extension point: each middleware wraps every api_call.
        # Empty by default → zero overhead, identical behavior. See middleware.py.
        self._middlewares = list(middlewares or [])
        self.recorder = CostRecorder(setup, rate_config, logger, cost_logger)
        self._services: dict[str, ServiceState] = {
            name: ServiceState(lim) for name, lim in rate_config.services.items()
        }

    @property
    def tracker(self):  # backwards-compat shim for tests/SDK reads
        return self.recorder.tracker

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
        """Run ``api_call(*args, **kwargs)`` through the gatekeeper.

        Blocks for a rate-limit slot (FIFO; raises ``QueueFullError`` past the
        configured depth), then retries transient failures with linear backoff.
        On success records token usage + cost (enforcing the budget). ``service``
        selects the per-service limit bucket. Returns the call's result.
        """
        st = self._state(service)
        self._wait_for_slot(st)
        last_exc: BaseException | None = None
        call = compose(self._middlewares, api_call)  # no-op when no middlewares
        with st.semaphore:
            with st.lock:
                st.in_flight += 1
            try:
                for attempt in range(1, st.limit.max_retries + 2):
                    try:
                        result = call(*args, **kwargs)
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
                    self.recorder.record(result)
                    return result
                raise ApiCallFailedError(f"exhausted retries: {last_exc}") from last_exc
            finally:
                with st.lock:
                    st.in_flight -= 1

    def get_queue_status(self, service: str = "default") -> QueueStatus:
        st = self._state(service)
        with st.lock:
            return QueueStatus(service, st.pending, st.in_flight, len(st.minute), len(st.hour))

    def reset_costs(self) -> None:
        """Start a fresh per-run token/cost report."""
        self.recorder.reset()

    def get_token_summary(self) -> dict:
        return self.recorder.summary()
