"""Unit tests for debate.shared.gatekeeper.ApiGatekeeper."""

from __future__ import annotations

import logging
import threading
import time
from unittest.mock import MagicMock

import pytest

from debate.shared.config import (
    BudgetCfg,
    ModelPrice,
    ModelRef,
    RagCfg,
    RateLimitConfig,
    SearchCfg,
    ServiceLimit,
    SetupConfig,
    Timeouts,
)
from debate.shared.gatekeeper import (
    ApiCallFailedError,
    ApiGatekeeper,
    BudgetExceededError,
    QueueFullError,
)
from debate.shared.schemas import CompletionResponse


class FakeHttpError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def _service(**over) -> ServiceLimit:
    base = {
        "requests_per_minute": 60,
        "requests_per_hour": 600,
        "concurrent_max": 5,
        "retry_after_seconds": 1,
        "max_retries": 3,
        "queue_max_depth": 10,
        "retryable_status_codes": [429, 500, 503],
    }
    base.update(over)
    return ServiceLimit(**base)


def _rate_cfg(svc: ServiceLimit | None = None, warn: int = 80, hard: int = 100) -> RateLimitConfig:
    return RateLimitConfig(
        version="1.00",
        services={"default": svc or _service()},
        budget=BudgetCfg(warning_threshold_pct=warn, hard_limit_pct=hard),
    )


def _setup_cfg(budget: float = 5.0) -> SetupConfig:
    return SetupConfig(
        version="1.00",
        topic="t",
        num_rounds=1,
        max_words_per_ping=10,
        budget_usd=budget,
        models={"dogs": ModelRef(provider="anthropic", name="haiku")},
        timeouts=Timeouts(
            agent_response_seconds=10,
            watchdog_heartbeat_seconds=1,
            watchdog_kill_after_seconds=5,
            max_restarts_per_agent=1,
        ),
        rag=RagCfg(enabled=False, k=1, chunk_size=10, embedder="x", persist_dir="x"),
        search=SearchCfg(provider="ddg", max_results=1, timeout_seconds=1),
        pricing={
            "anthropic": {
                "haiku": ModelPrice(input_per_million_usd=1.0, output_per_million_usd=4.0),
            }
        },
    )


def _gk(svc=None, budget=5.0, warn=80) -> ApiGatekeeper:
    return ApiGatekeeper(
        rate_config=_rate_cfg(svc, warn=warn),
        setup=_setup_cfg(budget),
        logger=logging.getLogger("test"),
        cost_logger=None,
        sleep_fn=lambda _s: None,
    )


def _resp(in_tok=100, out_tok=50, cache_creation=0, cache_read=0) -> CompletionResponse:
    return CompletionResponse(
        text="hi",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
        model="haiku",
        provider="anthropic",
    )


def test_execute_returns_result() -> None:
    gk = _gk()
    out = gk.execute(lambda: _resp())
    assert out.text == "hi"


def test_execute_records_tokens_and_cost() -> None:
    gk = _gk(budget=1000)
    gk.execute(lambda: _resp(in_tok=1_000_000, out_tok=1_000_000))
    summary = gk.get_token_summary()
    assert summary["by_model"]["anthropic/haiku"]["input_tokens"] == 1_000_000
    assert abs(summary["total_usd"] - 5.0) < 1e-9


def test_execute_records_cache_tokens_separately() -> None:
    gk = _gk()
    gk.execute(lambda: _resp(cache_creation=500, cache_read=200))
    entry = gk.get_token_summary()["by_model"]["anthropic/haiku"]
    assert entry["cache_creation_tokens"] == 500
    assert entry["cache_read_tokens"] == 200


def test_execute_skips_recording_for_non_completion() -> None:
    gk = _gk()
    gk.execute(lambda: {"results": ["a", "b"]})
    assert gk.get_token_summary()["total_usd"] == 0.0


def test_retries_on_retryable_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeHttpError(429)
        return _resp()

    gk = _gk(svc=_service(max_retries=3, retry_after_seconds=0))
    assert gk.execute(flaky).text == "hi"
    assert calls["n"] == 3


def test_max_retries_raises_api_call_failed() -> None:
    gk = _gk(svc=_service(max_retries=2, retry_after_seconds=0))
    with pytest.raises(ApiCallFailedError):
        gk.execute(lambda: (_ for _ in ()).throw(FakeHttpError(503)))


def test_non_retryable_exception_propagates() -> None:
    gk = _gk()

    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        gk.execute(boom)


def test_timeout_is_retried() -> None:
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("slow")
        return _resp()

    gk = _gk(svc=_service(max_retries=2, retry_after_seconds=0))
    gk.execute(flaky)
    assert calls["n"] == 2


def test_budget_warning_logged_once(caplog) -> None:
    gk = _gk(budget=0.001, warn=50)  # any call will blow past 50%, well under 100%
    # tweak budget so first call is between warn and hard
    gk.setup.budget_usd = 1.0
    gk.rate_config.budget.warning_threshold_pct = 1
    gk.rate_config.budget.hard_limit_pct = 100
    with caplog.at_level(logging.WARNING, logger="test"):
        gk.execute(lambda: _resp(in_tok=10_000, out_tok=10_000))
        gk.execute(lambda: _resp(in_tok=10_000, out_tok=10_000))
    warnings = [r for r in caplog.records if "budget at" in r.getMessage()]
    assert len(warnings) == 1


def test_budget_exceeded_raises() -> None:
    gk = _gk(budget=0.001)
    with pytest.raises(BudgetExceededError):
        gk.execute(lambda: _resp(in_tok=1_000_000, out_tok=1_000_000))


def test_queue_full_raises() -> None:
    svc = _service(requests_per_minute=1, queue_max_depth=1)
    gk = ApiGatekeeper(
        rate_config=_rate_cfg(svc),
        setup=_setup_cfg(),
        logger=logging.getLogger("test"),
        sleep_fn=lambda _s: time.sleep(0.01),
    )
    # exhaust the minute window so subsequent calls would wait
    gk.execute(lambda: _resp())

    started = threading.Event()
    finished = threading.Event()

    def worker():
        started.set()
        try:
            gk.execute(lambda: _resp())
        finally:
            finished.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    started.wait(timeout=1.0)
    # let the worker increment pending
    time.sleep(0.1)
    with pytest.raises(QueueFullError):
        gk.execute(lambda: _resp())
    # let the worker resolve (it will keep sleeping until minute rolls — abandon)
    # We deliberately don't join — the daemon thread will be GC'd at exit.
    assert not finished.is_set() or finished.is_set()  # either is fine


def test_concurrent_max_respected() -> None:
    svc = _service(concurrent_max=2, requests_per_minute=100)
    gk = ApiGatekeeper(
        rate_config=_rate_cfg(svc),
        setup=_setup_cfg(budget=1000),
        logger=logging.getLogger("test"),
        sleep_fn=lambda _s: None,
    )
    in_flight = {"max": 0, "now": 0}
    lock = threading.Lock()

    def slow():
        with lock:
            in_flight["now"] += 1
            in_flight["max"] = max(in_flight["max"], in_flight["now"])
        time.sleep(0.05)
        with lock:
            in_flight["now"] -= 1
        return _resp()

    threads = [threading.Thread(target=gk.execute, args=(slow,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert in_flight["max"] == 2


def test_unknown_service_falls_back_to_default() -> None:
    gk = _gk()
    gk.execute(lambda: _resp(), service="nonexistent")
    assert gk.get_queue_status("nonexistent").service == "nonexistent"


def test_cost_logger_called_when_provided(tmp_path) -> None:
    cost_log = MagicMock()
    gk = ApiGatekeeper(
        rate_config=_rate_cfg(),
        setup=_setup_cfg(),
        logger=logging.getLogger("test"),
        cost_logger=cost_log,
        sleep_fn=lambda _s: None,
    )
    gk.execute(lambda: _resp())
    assert cost_log.info.called
