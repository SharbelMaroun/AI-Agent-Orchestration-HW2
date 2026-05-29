"""Process orchestrator tests with a fake runtime."""

from __future__ import annotations

from datetime import datetime, timezone

from debate.services import process_orchestrator as mod
from debate.services.process_orchestrator import ProcessOrchestrator
from debate.shared.config import load_setup
from debate.shared.schemas import Ping, Score, Verdict, YourTurn


class FakeRuntime:
    def __init__(self, *_args, **_kwargs) -> None:
        self.sent = []
        self.costs = []

    def start_all(self) -> None:
        self.started = True

    def send(self, agent_id, payload) -> None:
        self.sent.append((agent_id, payload))

    def recv(self, agent_id):
        payload = self.sent[-1][1]
        if isinstance(payload, YourTurn):
            return Ping(
                round=payload.round,
                side=agent_id,
                text=f"{agent_id} arg",
                citations=[],
                refers_to_ping=payload.previous_ping.round if payload.previous_ping else None,
                timestamp=datetime.now(timezone.utc),
            )
        if isinstance(payload, Ping):
            return Score(
                ping_round=payload.round,
                side=payload.side,
                structure=1,
                logos=1,
                pathos=1,
                ethos=1,
                clash=1,
                rationale="ok",
            )
        return Verdict(
            winner="dogs",
            dogs_total=10,
            cats_total=8,
            margin=2,
            written_rationale="ok",
        )

    def shutdown(self) -> None:
        self.stopped = True
        self.costs.append({"total_usd": 1.0, "by_model": {}, "cache_read_pct": 0.0})


def test_process_orchestrator_runs_with_queue_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "ProcessRuntime", FakeRuntime)
    setup = load_setup("config/setup.json")
    data = setup.model_dump()
    data["num_rounds"] = 1
    setup = type(setup).model_validate(data)

    events = []
    orch = ProcessOrchestrator(
        setup,
        results_dir=tmp_path,
        on_event=lambda kind, payload: events.append((kind, payload)),
        coin_flip=lambda: 1,
    )
    result = orch.run_debate()

    assert len(result.pings) == 2
    assert len(result.scores) == 2
    assert result.verdict.winner == "dogs"
    assert result.cost_report["total_usd"] == 1.0
    assert [kind for kind, _payload in events] == [
        "announcement",
        "debate_start",
        "round_start",
        "ping",
        "score",
        "ping",
        "score",
        "round_end",
        "verdict",
        "debate_end",
    ]
    assert list(tmp_path.glob("debate_*.json"))
