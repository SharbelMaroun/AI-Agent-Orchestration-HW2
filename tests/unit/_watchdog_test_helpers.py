"""Test doubles + factories for watchdog tests. Filename prefix `_` so
pytest does not collect it as a test module."""

from __future__ import annotations

import logging

from debate.services.watchdog import Watchdog, WatchdogConfig


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


def cfg(**over) -> WatchdogConfig:
    base = {
        "heartbeat_seconds": 1.0,
        "kill_after_seconds": 5.0,
        "max_restarts_per_agent": 2,
        "terminate_grace_seconds": 0.0,
        "poll_interval_seconds": 0.01,
    }
    base.update(over)
    return WatchdogConfig(**base)


def wd(clock: FakeClock, **over) -> Watchdog:
    return Watchdog(
        config=cfg(**over),
        logger=logging.getLogger("test.wd"),
        clock=clock,
        sleep_fn=lambda _s: None,
    )
