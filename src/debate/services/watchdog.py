"""Watchdog — heartbeat monitoring + kill-and-restart for hung agents.

See docs/PRD_watchdog.md. Runs as a daemon thread in the parent process; child
agent processes call `heartbeat(agent_id)` periodically through the heartbeat
queue. If a child's last heartbeat is older than `kill_after_seconds`, the
watchdog terminates and restarts it via the registered `restart_fn`.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class WatchdogFatalError(Exception):
    """Raised when an agent exceeds max_restarts and cannot recover."""


@dataclass
class _Entry:
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
class _Clock:
    fn: Callable[[], float] = field(default=time.monotonic)

    def __call__(self) -> float:
        return self.fn()


class Watchdog:
    """Daemon-thread heartbeat monitor."""

    def __init__(
        self,
        config: WatchdogConfig,
        logger: logging.Logger | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("debate.watchdog")
        self._clock = clock
        self._sleep = sleep_fn
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._fatal_agents: list[str] = []

    def register(self, agent_id: str, process: Any, restart_fn: Callable[[], Any]) -> None:
        with self._lock:
            self._entries[agent_id] = _Entry(
                process=process, restart_fn=restart_fn, last_seen=self._clock()
            )

    def heartbeat(self, agent_id: str) -> None:
        with self._lock:
            entry = self._entries.get(agent_id)
            if entry is not None:
                entry.last_seen = self._clock()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        with self._lock:
            for agent_id, entry in self._entries.items():
                self._terminate(agent_id, entry.process)

    def fatal_agents(self) -> list[str]:
        with self._lock:
            return list(self._fatal_agents)

    def check_once(self) -> None:
        """Single pass over all registered agents. Exposed for deterministic
        testing (no need to spin up the daemon thread)."""
        now = self._clock()
        with self._lock:
            stale = [
                (aid, e)
                for aid, e in self._entries.items()
                if not e.fatal and now - e.last_seen > self.config.kill_after_seconds
            ]
        for agent_id, entry in stale:
            self._handle_timeout(agent_id, entry)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.check_once()
            except Exception:
                self.logger.exception("watchdog loop iteration failed")
            self._sleep(self.config.poll_interval_seconds)

    def _handle_timeout(self, agent_id: str, entry: _Entry) -> None:
        self.logger.warning("AGENT_TIMEOUT agent=%s last_seen=%.3f", agent_id, entry.last_seen)
        self._terminate(agent_id, entry.process)
        with self._lock:
            entry.restart_count += 1
            if entry.restart_count > self.config.max_restarts_per_agent:
                entry.fatal = True
                self._fatal_agents.append(agent_id)
                self.logger.error("AGENT_DEAD agent=%s restarts_exhausted", agent_id)
                raise WatchdogFatalError(f"{agent_id} exceeded max_restarts")
        try:
            new_proc = entry.restart_fn()
        except Exception:
            self.logger.exception("restart_fn failed agent=%s", agent_id)
            return
        with self._lock:
            entry.process = new_proc if new_proc is not None else entry.process
            entry.last_seen = self._clock()
        self.logger.info("AGENT_RESTARTED agent=%s count=%d", agent_id, entry.restart_count)

    def _terminate(self, agent_id: str, process: Any) -> None:
        if process is None:
            return
        terminate = getattr(process, "terminate", None)
        kill = getattr(process, "kill", None)
        is_alive = getattr(process, "is_alive", lambda: False)
        try:
            if terminate is not None:
                terminate()
            self._sleep(self.config.terminate_grace_seconds)
            if is_alive() and kill is not None:
                kill()
        except Exception:
            self.logger.exception("terminate failed agent=%s", agent_id)
