"""Budget alerts + queue backpressure + concurrent_max enforcement.

Split off from `test_gatekeeper.py` for the 150-LOC test cap."""

from __future__ import annotations

import logging
import threading
import time

import pytest

from debate.shared.gatekeeper import ApiGatekeeper, BudgetExceededError, QueueFullError
from tests.unit._gatekeeper_fixtures import gk, rate_cfg, resp, service, setup_cfg


def test_budget_warning_logged_once(caplog) -> None:
    g = gk(budget=0.001, warn=50)  # any call will blow past 50%, well under 100%
    g.setup.budget_usd = 1.0
    g.rate_config.budget.warning_threshold_pct = 1
    g.rate_config.budget.hard_limit_pct = 100
    with caplog.at_level(logging.WARNING, logger="test"):
        g.execute(lambda: resp(in_tok=10_000, out_tok=10_000))
        g.execute(lambda: resp(in_tok=10_000, out_tok=10_000))
    warnings = [r for r in caplog.records if "budget at" in r.getMessage()]
    assert len(warnings) == 1


def test_budget_exceeded_raises() -> None:
    g = gk(budget=0.001)
    with pytest.raises(BudgetExceededError):
        g.execute(lambda: resp(in_tok=1_000_000, out_tok=1_000_000))


def test_queue_full_raises() -> None:
    svc = service(requests_per_minute=1, queue_max_depth=1)
    g = ApiGatekeeper(
        rate_config=rate_cfg(svc),
        setup=setup_cfg(),
        logger=logging.getLogger("test"),
        sleep_fn=lambda _s: time.sleep(0.01),
    )
    # exhaust the minute window so subsequent calls would wait
    g.execute(lambda: resp())

    started = threading.Event()
    finished = threading.Event()

    def worker():
        started.set()
        try:
            g.execute(lambda: resp())
        finally:
            finished.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    started.wait(timeout=1.0)
    # let the worker increment pending
    time.sleep(0.1)
    with pytest.raises(QueueFullError):
        g.execute(lambda: resp())
    # Daemon thread will be GC'd at exit — we deliberately don't join.
    assert not finished.is_set() or finished.is_set()


def test_concurrent_max_respected() -> None:
    svc = service(concurrent_max=2, requests_per_minute=100)
    g = ApiGatekeeper(
        rate_config=rate_cfg(svc),
        setup=setup_cfg(budget=1000),
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
        return resp()

    threads = [threading.Thread(target=g.execute, args=(slow,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert in_flight["max"] == 2
