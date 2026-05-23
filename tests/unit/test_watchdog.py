"""Unit tests for debate.services.watchdog.

Shared test doubles (`FakeProcess`, `FakeClock`) and factories (`cfg`, `wd`)
live in `_watchdog_test_helpers.py` so this file stays under the raw cap."""

from __future__ import annotations

import pytest

from debate.services.watchdog import WatchdogConfig, WatchdogFatalError
from tests.unit._watchdog_test_helpers import FakeClock, FakeProcess, wd


def test_healthy_run_no_restart() -> None:
    clock = FakeClock()
    w = wd(clock)
    proc = FakeProcess()
    w.register("dogs", proc, lambda: pytest.fail("should not restart"))
    for _ in range(3):
        clock.advance(1.0)
        w.heartbeat("dogs")
        w.check_once()
    assert not proc.terminated


def test_detects_timeout_and_invokes_restart() -> None:
    clock = FakeClock()
    w = wd(clock)
    proc = FakeProcess()
    new_proc = FakeProcess()
    calls = {"n": 0}

    def restart():
        calls["n"] += 1
        return new_proc

    w.register("dogs", proc, restart)
    clock.advance(10.0)
    w.check_once()
    assert proc.terminated
    assert calls["n"] == 1


def test_max_restarts_raises_fatal() -> None:
    clock = FakeClock()
    w = wd(clock, max_restarts_per_agent=1)
    w.register("dogs", FakeProcess(), lambda: FakeProcess())
    clock.advance(10.0)
    w.check_once()  # restart #1
    clock.advance(10.0)
    with pytest.raises(WatchdogFatalError):
        w.check_once()  # restart #2 → exceeds max=1
    assert "dogs" in w.fatal_agents()


def test_fatal_agent_skipped_on_next_check() -> None:
    clock = FakeClock()
    w = wd(clock, max_restarts_per_agent=0)
    w.register("dogs", FakeProcess(), lambda: FakeProcess())
    clock.advance(10.0)
    with pytest.raises(WatchdogFatalError):
        w.check_once()
    clock.advance(10.0)
    w.check_once()  # should not raise — agent already marked fatal


def test_heartbeat_after_register_resets_last_seen() -> None:
    clock = FakeClock()
    w = wd(clock)
    w.register("dogs", FakeProcess(), lambda: FakeProcess())
    clock.advance(4.9)
    w.heartbeat("dogs")  # now last_seen = 4.9
    clock.advance(4.9)  # total 9.8, but only 4.9 since heartbeat
    w.check_once()  # 4.9 ≤ 5.0 → no timeout


def test_stop_terminates_registered_processes() -> None:
    clock = FakeClock()
    w = wd(clock)
    p1, p2 = FakeProcess(), FakeProcess()
    w.register("dogs", p1, lambda: FakeProcess())
    w.register("cats", p2, lambda: FakeProcess())
    w.stop()
    assert p1.terminated
    assert p2.terminated


def test_unknown_heartbeat_is_safe() -> None:
    wd(FakeClock()).heartbeat("ghost")  # no entry registered — must not raise


def test_restart_fn_exception_does_not_propagate() -> None:
    clock = FakeClock()
    w = wd(clock)

    def bad_restart():
        raise RuntimeError("nope")

    w.register("dogs", FakeProcess(), bad_restart)
    clock.advance(10.0)
    w.check_once()  # must not raise


def test_config_from_timeouts() -> None:
    class T:
        watchdog_heartbeat_seconds = 5
        watchdog_kill_after_seconds = 90
        max_restarts_per_agent = 3

    c = WatchdogConfig.from_timeouts(T())
    assert c.heartbeat_seconds == 5
    assert c.kill_after_seconds == 90
    assert c.max_restarts_per_agent == 3
