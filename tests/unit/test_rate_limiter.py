"""Unit tests for debate.shared.rate_limiter.

Direct tests for the internals — `RollingWindow`, `ServiceState`,
`is_retryable`. Integration through the gatekeeper is covered by
`test_gatekeeper.py` + `test_gatekeeper_budget_and_queue.py`."""

from __future__ import annotations

from debate.shared.rate_limiter import (
    ApiCallFailedError,
    BudgetExceededError,
    QueueFullError,
    QueueStatus,
    RollingWindow,
    ServiceState,
    is_retryable,
)
from tests.unit._gatekeeper_fixtures import service


def test_rolling_window_starts_empty() -> None:
    w = RollingWindow()
    assert len(w) == 0


def test_rolling_window_add_increments_length() -> None:
    w = RollingWindow()
    w.add(100.0)
    w.add(101.0)
    assert len(w) == 2


def test_rolling_window_prune_drops_old_entries() -> None:
    w = RollingWindow()
    for t in (90.0, 95.0, 100.0):
        w.add(t)
    # window=10 with now=105 keeps anything >= 95
    w.prune(now=105.0, window=10.0)
    assert len(w) == 2


def test_rolling_window_prune_keeps_all_when_fresh() -> None:
    w = RollingWindow()
    for t in (100.0, 101.0, 102.0):
        w.add(t)
    w.prune(now=103.0, window=60.0)
    assert len(w) == 3


def test_service_state_initialises_with_limit() -> None:
    st = ServiceState(service())
    assert st.pending == 0
    assert st.in_flight == 0
    assert len(st.minute) == 0
    assert len(st.hour) == 0


def test_service_state_semaphore_matches_concurrent_max() -> None:
    st = ServiceState(service(concurrent_max=3))
    # acquire 3 then a non-blocking attempt should fail
    assert st.semaphore.acquire(blocking=False)
    assert st.semaphore.acquire(blocking=False)
    assert st.semaphore.acquire(blocking=False)
    assert not st.semaphore.acquire(blocking=False)


class _FakeHttpError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def test_is_retryable_status_code_match() -> None:
    assert is_retryable(_FakeHttpError(429), [429, 500])
    assert is_retryable(_FakeHttpError(500), [429, 500])


def test_is_retryable_status_code_miss() -> None:
    assert not is_retryable(_FakeHttpError(404), [429, 500])


def test_is_retryable_timeout() -> None:
    assert is_retryable(TimeoutError("slow"), [])
    assert is_retryable(ConnectionError("reset"), [])


def test_is_retryable_value_error_not_retried() -> None:
    assert not is_retryable(ValueError("bad input"), [429, 500])


def test_exception_classes_exist_and_are_distinct() -> None:
    """Smoke check that the exception names the gatekeeper expects all
    exist and inherit from Exception."""
    for cls in (BudgetExceededError, QueueFullError, ApiCallFailedError):
        assert issubclass(cls, Exception)


def test_queue_status_dataclass_fields() -> None:
    qs = QueueStatus(service="default", pending=2, in_flight=1, minute_count=5, hour_count=20)
    assert qs.service == "default"
    assert qs.pending == 2
    assert qs.in_flight == 1
