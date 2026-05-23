"""Dataclasses for the Watchdog. Extracted from `watchdog.py` to keep
that file under the 150-line raw cap."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class WatchdogFatalError(Exception):
    """Raised when an agent exceeds max_restarts and cannot recover."""


@dataclass
class Entry:
    """Per-agent state: process handle + restart factory + heartbeat clock."""

    process: Any
    restart_fn: Callable[[], Any]
    last_seen: float
    restart_count: int = 0
    fatal: bool = False


@dataclass
class WatchdogConfig:
    heartbeat_seconds: float
    kill_after_seconds: float
    max_restarts_per_agent: int
    terminate_grace_seconds: float = 2.0
    poll_interval_seconds: float = 0.5

    @classmethod
    def from_timeouts(cls, t: Any) -> WatchdogConfig:
        return cls(
            heartbeat_seconds=t.watchdog_heartbeat_seconds,
            kill_after_seconds=t.watchdog_kill_after_seconds,
            max_restarts_per_agent=t.max_restarts_per_agent,
        )


@dataclass
class Clock:
    """Injectable monotonic clock — tests pass a deterministic fn."""

    fn: Callable[[], float] = field(default=time.monotonic)

    def __call__(self) -> float:
        return self.fn()
