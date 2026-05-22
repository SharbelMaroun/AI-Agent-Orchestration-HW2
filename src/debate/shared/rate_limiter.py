"""Internal building blocks for ApiGatekeeper.

Kept in a sibling module so `gatekeeper.py` stays under the 150-LOC cap. Not
part of the public API — callers should use `ApiGatekeeper` from
`gatekeeper.py`.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass

from .config import ServiceLimit


class BudgetExceededError(Exception):
    """Cumulative cost crossed `hard_limit_pct` of the configured budget."""


class QueueFullError(Exception):
    """Backpressure queue is full — request rejected rather than queued."""


class ApiCallFailedError(Exception):
    """API call exhausted all retries; wraps the last underlying exception."""


@dataclass
class QueueStatus:
    service: str
    pending: int
    in_flight: int
    minute_count: int
    hour_count: int


class RollingWindow:
    """Rolling-window timestamp counter (O(1) amortised per add/prune)."""

    __slots__ = ("ts",)

    def __init__(self) -> None:
        self.ts: deque[float] = deque()

    def prune(self, now: float, window: float) -> None:
        cutoff = now - window
        while self.ts and self.ts[0] < cutoff:
            self.ts.popleft()

    def add(self, now: float) -> None:
        self.ts.append(now)

    def __len__(self) -> int:
        return len(self.ts)


class ServiceState:
    """Per-service rate-limit state — windows, semaphore, counters, lock."""

    def __init__(self, limit: ServiceLimit) -> None:
        self.limit = limit
        self.minute = RollingWindow()
        self.hour = RollingWindow()
        self.semaphore = threading.Semaphore(limit.concurrent_max)
        self.lock = threading.Lock()
        self.pending = 0
        self.in_flight = 0


def is_retryable(exc: BaseException, codes: list[int]) -> bool:
    """True if `exc` is a transient failure that should trigger a retry."""
    status = getattr(exc, "status_code", None)
    if status in codes:
        return True
    return isinstance(exc, TimeoutError | ConnectionError)
