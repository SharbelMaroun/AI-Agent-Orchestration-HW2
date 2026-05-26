"""Process runtime unit tests without spawning OS processes."""

from __future__ import annotations

from debate.services import process_runtime as mod
from debate.services.process_runtime import ProcessRuntime, merge_costs
from debate.shared.config import load_setup
from debate.shared.schemas import Heartbeat


class FakeQueue:
    def __init__(self) -> None:
        self.items = []

    def put(self, item) -> None:
        self.items.append(item)

    def get(self, timeout=None):
        del timeout
        if not self.items:
            raise mod.Empty
        return self.items.pop(0)

    def get_nowait(self):
        return self.get()


class FakeProcess:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.started = False

    def start(self) -> None:
        self.started = True

    def join(self, timeout=None) -> None:
        self.join_timeout = timeout


class FakeContext:
    def Queue(self):
        return FakeQueue()

    def Process(self, *args, **kwargs):
        return FakeProcess(*args, **kwargs)


class FakeWatchdog:
    def __init__(self, _cfg) -> None:
        self.registered = []
        self.beats = []

    def register(self, agent_id, process, restart_fn) -> None:
        self.registered.append((agent_id, process, restart_fn))

    def heartbeat(self, agent_id) -> None:
        self.beats.append(agent_id)

    def check_once(self) -> None:
        self.checked = True

    def stop(self) -> None:
        self.stopped = True


def test_runtime_starts_sends_receives_and_drains(monkeypatch):
    monkeypatch.setattr(mod.mp, "get_context", lambda _name: FakeContext())
    monkeypatch.setattr(mod, "Watchdog", FakeWatchdog)
    setup = load_setup("config/setup.json")
    runtime = ProcessRuntime(setup, "config/rate_limits.json", "config/logging_config.json")

    runtime.start_all()
    assert sorted(runtime.inboxes) == ["cats", "dogs", "judge"]
    assert all(proc.started for proc in runtime.procs.values())

    runtime.send("dogs", "hello")
    assert runtime.inboxes["dogs"].items == ["hello"]
    runtime.heartbeat_q.put(Heartbeat(agent_id="dogs", timestamp="2026-01-01T00:00:00Z"))
    runtime.drain_heartbeats()
    assert runtime.watchdog.beats == ["dogs"]

    runtime.outbox.put({"agent": "dogs", "kind": "result", "payload": "pong"})
    assert runtime.recv("dogs") == "pong"


def test_merge_costs_combines_model_entries():
    report = merge_costs(
        [
            {
                "total_usd": 1.0,
                "by_model": {
                    "openai/x": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cache_creation_tokens": 0,
                        "cache_read_tokens": 5,
                        "cost_usd": 1.0,
                    }
                },
            }
        ]
    )
    assert report["total_usd"] == 1.0
    assert report["by_model"]["openai/x"]["input_tokens"] == 10
    assert report["cache_read_pct"] == 100 * 5 / 15
