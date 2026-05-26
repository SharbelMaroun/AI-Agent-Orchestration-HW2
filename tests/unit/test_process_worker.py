"""Child process worker tests using fake dependencies."""

from __future__ import annotations

from debate.services import process_worker as mod
from debate.services.process_worker import agent_process_main
from debate.shared.config import load_setup


class FakeQueue:
    def __init__(self, items=None) -> None:
        self.items = list(items or [])

    def put(self, item) -> None:
        self.items.append(item)

    def get(self, timeout=None):
        del timeout
        if not self.items:
            raise mod.Empty
        return self.items.pop(0)


class FakeGatekeeper:
    def get_token_summary(self):
        return {"total_usd": 0.0, "by_model": {}, "cache_read_pct": 0.0}


class FakeAgent:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def receive(self, envelope):
        return f"handled:{envelope}"


def test_worker_sends_cost_on_shutdown(monkeypatch):
    monkeypatch.setattr(mod, "load_env", lambda _path: None)
    monkeypatch.setattr(mod, "_build_gatekeeper", lambda *_args: FakeGatekeeper())
    monkeypatch.setattr(mod, "_build_agent", lambda *_args: FakeAgent())
    setup = load_setup("config/setup.json")
    inbox, outbox, heartbeat = FakeQueue([None]), FakeQueue(), FakeQueue()

    agent_process_main(
        "dogs",
        setup.model_dump(),
        "config/rate_limits.json",
        "config/logging_config.json",
        inbox,
        outbox,
        heartbeat,
    )

    assert heartbeat.items
    assert outbox.items[0]["kind"] == "cost"


def test_worker_forwards_agent_result(monkeypatch):
    monkeypatch.setattr(mod, "load_env", lambda _path: None)
    monkeypatch.setattr(mod, "_build_gatekeeper", lambda *_args: FakeGatekeeper())
    monkeypatch.setattr(mod, "_build_agent", lambda *_args: FakeAgent())
    setup = load_setup("config/setup.json")
    inbox, outbox, heartbeat = FakeQueue(["x", None]), FakeQueue(), FakeQueue()

    agent_process_main(
        "cats",
        setup.model_dump(),
        "config/rate_limits.json",
        "config/logging_config.json",
        inbox,
        outbox,
        heartbeat,
    )

    assert outbox.items[0] == {"agent": "cats", "kind": "result", "payload": "handled:x"}
