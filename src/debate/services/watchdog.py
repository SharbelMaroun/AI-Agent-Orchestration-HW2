"""Watchdog — heartbeat monitoring + kill-and-restart for hung agents.

See docs/PRD_watchdog.md. Phase 4.2.
"""


class WatchdogFatalError(Exception):
    """Raised when an agent exceeds max_restarts and cannot recover."""


class Watchdog:
    """Daemon thread that monitors agent heartbeats. Phase 4.2."""

    def register(self, agent_id: str, process: object, restart_fn: object) -> None:
        """Add an agent to the watch list. Phase 4.2."""
        raise NotImplementedError

    def heartbeat(self, agent_id: str) -> None:
        """Record a heartbeat from an agent. Phase 4.2."""
        raise NotImplementedError

    def start(self) -> None:
        """Spawn the watchdog thread. Phase 4.2."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the watchdog thread cleanly. Phase 4.2."""
        raise NotImplementedError
