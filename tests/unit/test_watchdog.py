"""Unit tests for debate.services.watchdog."""

from __future__ import annotations

import logging

import pytest

from debate.services.watchdog import Watchdog, WatchdogConfig, WatchdogFatalError


class FakeProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False
        self._alive = True

    def terminate(self) -> None:
        self.terminated = True
        self._alive = False

    def kill(self) -> None:
        self.killed = True
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _cfg(**over) -> WatchdogConfig:
    base = {
        "heartbeat_seconds": 1.0,
        "kill_after_seconds": 5.0,
        "max_restarts_per_agent": 2,
        "terminate_grace_seconds": 0.0,
        "poll_interval_seconds": 0.01,
    }
    base.update(over)
    return WatchdogConfig(**base)


def _wd(clock: FakeClock, **over) -> Watchdog:
    return Watchdog(
        config=_cfg(**over),
        logger=logging.getLogger("test.wd"),
        clock=clock,
        sleep_fn=lambda _s: None,
    )


def test_healthy_run_no_restart() -> None:
    clock = FakeClock()
    wd = _wd(clock)
    proc = FakeProcess()
    restart = lambda: pytest.fail("should not restart")  # noqa: E731
    wd.register("dogs", proc, restart)
    for _ in range(3):
        clock.advance(1.0)
        wd.heartbeat("dogs")
        wd.check_once()
    assert not proc.terminated


def test_detects_timeout_and_invokes_restart() -> None:
    clock = FakeClock()
    wd = _wd(clock)
    proc = FakeProcess()
    new_proc = FakeProcess()
    calls = {"n": 0}

    def restart():
        calls["n"] += 1
        return new_proc

    wd.register("dogs", proc, restart)
    clock.advance(10.0)
    wd.check_once()
    assert proc.terminated
    assert calls["n"] == 1


def test_max_restarts_raises_fatal() -> None:
    clock = FakeClock()
    wd = _wd(clock, max_restarts_per_agent=1)
    proc = FakeProcess()
    wd.register("dogs", proc, lambda: FakeProcess())
    clock.advance(10.0)
    wd.check_once()  # restart #1
    clock.advance(10.0)
    with pytest.raises(WatchdogFatalError):
        wd.check_once()  # restart #2 → exceeds max=1
    assert "dogs" in wd.fatal_agents()


def test_fatal_agent_skipped_on_next_check() -> None:
    clock = FakeClock()
    wd = _wd(clock, max_restarts_per_agent=0)
    wd.register("dogs", FakeProcess(), lambda: FakeProcess())
    clock.advance(10.0)
    with pytest.raises(WatchdogFatalError):
        wd.check_once()
    clock.advance(10.0)
    wd.check_once()  # should not raise — agent already marked fatal


def test_heartbeat_after_register_resets_last_seen() -> None:
    clock = FakeClock()
    wd = _wd(clock)
    wd.register("dogs", FakeProcess(), lambda: FakeProcess())
    clock.advance(4.9)
    wd.heartbeat("dogs")  # now last_seen = 4.9
    clock.advance(4.9)    # total 9.8, but only 4.9 since heartbeat
    wd.check_once()       # 4.9 ≤ 5.0 → no timeout
    # If the heartbeat had been ignored, this would have fired a restart.


def test_stop_terminates_registered_processes() -> None:
    clock = FakeClock()
    wd = _wd(clock)
    p1, p2 = FakeProcess(), FakeProcess()
    wd.register("dogs", p1, lambda: FakeProcess())
    wd.register("cats", p2, lambda: FakeProcess())
    wd.stop()
    assert p1.terminated
    assert p2.terminated


def test_unknown_heartbeat_is_safe() -> None:
    wd = _wd(FakeClock())
    wd.heartbeat("ghost")  # no entry registered — must not raise


def test_restart_fn_exception_does_not_propagate() -> None:
    clock = FakeClock()
    wd = _wd(clock)

    def bad_restart():
        raise RuntimeError("nope")

    wd.register("dogs", FakeProcess(), bad_restart)
    clock.advance(10.0)
    wd.check_once()  # must not raise


def test_config_from_timeouts() -> None:
    class T:
        watchdog_heartbeat_seconds = 5
        watchdog_kill_after_seconds = 90
        max_restarts_per_agent = 3
    cfg = WatchdogConfig.from_timeouts(T())
    assert cfg.heartbeat_seconds == 5
    assert cfg.kill_after_seconds == 90
    assert cfg.max_restarts_per_agent == 3
