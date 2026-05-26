"""Queue/process plumbing for the multiprocessing debate orchestrator."""

from __future__ import annotations

import multiprocessing as mp
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty
from typing import Any

from debate.services._watchdog_models import WatchdogConfig
from debate.services.process_worker import agent_process_main
from debate.services.watchdog import Watchdog
from debate.shared.config import SetupConfig
from debate.shared.schemas import Heartbeat


class ProcessRuntime:
    def __init__(
        self,
        setup: SetupConfig,
        rate_limits_path: str | Path,
        logging_path: str | Path,
    ) -> None:
        self.setup = setup
        self.rate_limits_path = str(rate_limits_path)
        self.logging_path = str(logging_path)
        self.costs: list[dict] = []
        self.ctx = mp.get_context("spawn")
        self.inboxes: dict[str, Any] = {}
        self.procs: dict[str, Any] = {}
        self.outbox = self.ctx.Queue()
        self.heartbeat_q = self.ctx.Queue()
        self.watchdog = Watchdog(WatchdogConfig.from_timeouts(setup.timeouts))

    def start_all(self) -> None:
        for kind in ("dogs", "cats", "judge"):
            self.inboxes[kind] = self.ctx.Queue()
            self.procs[kind] = self.spawn(kind)
            self.watchdog.register(kind, self.procs[kind], lambda k=kind: self.spawn(k))

    def spawn(self, kind: str) -> Any:
        proc = self.ctx.Process(
            target=agent_process_main,
            args=(
                kind,
                self.setup.model_dump(),
                self.rate_limits_path,
                self.logging_path,
                self.inboxes[kind],
                self.outbox,
                self.heartbeat_q,
            ),
            name=f"debate-{kind}",
        )
        proc.start()
        self.procs[kind] = proc
        return proc

    def send(self, agent_id: str, payload: Any) -> None:
        self.inboxes[agent_id].put(payload)

    def recv(self, agent_id: str) -> Any:
        while True:
            self.drain_heartbeats()
            self.watchdog.check_once()
            try:
                msg = self.outbox.get(timeout=0.2)
            except Empty:
                continue
            if msg["kind"] == "cost":
                self.costs.append(msg["payload"])
                continue
            if msg["kind"] == "error":
                raise RuntimeError(f"{msg['agent']} failed: {msg['payload']}")
            if msg["agent"] == agent_id:
                return msg["payload"]

    def drain_heartbeats(self) -> None:
        while True:
            try:
                beat = self.heartbeat_q.get_nowait()
            except Empty:
                return
            if isinstance(beat, Heartbeat):
                self.watchdog.heartbeat(beat.agent_id)

    def shutdown(self) -> None:
        for inbox in self.inboxes.values():
            inbox.put(None)
        deadline = datetime.now(timezone.utc).timestamp() + 5
        while len(self.costs) < 3 and datetime.now(timezone.utc).timestamp() < deadline:
            self.drain_heartbeats()
            try:
                msg = self.outbox.get(timeout=0.2)
            except Empty:
                continue
            if msg["kind"] == "cost":
                self.costs.append(msg["payload"])
        self.watchdog.stop()
        for proc in self.procs.values():
            proc.join(timeout=1.0)


def merge_costs(reports: list[dict]) -> dict:
    merged = {"total_usd": 0.0, "by_model": {}, "cache_read_pct": 0.0}
    input_like = cache_read = 0
    for report in reports:
        merged["total_usd"] += report.get("total_usd", 0.0)
        for key, entry in report.get("by_model", {}).items():
            target = merged["by_model"].setdefault(key, dict.fromkeys(entry, 0))
            for field, value in entry.items():
                target[field] += value
                if field in {"input_tokens", "cache_creation_tokens", "cache_read_tokens"}:
                    input_like += value
                if field == "cache_read_tokens":
                    cache_read += value
    if input_like:
        merged["cache_read_pct"] = 100.0 * cache_read / input_like
    return merged
