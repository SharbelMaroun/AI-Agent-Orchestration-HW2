"""BaseAgent tests (Phase 3.4)."""

from __future__ import annotations

import queue
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from debate.services.agents.base_agent import BaseAgent
from debate.shared.schemas import ChatMessage, CompletionResponse, Heartbeat


class _ConcreteAgent(BaseAgent):
    """Minimal subclass so the ABC can be instantiated in tests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received: list[object] = []

    def receive(self, envelope):
        self.received.append(envelope)
        return envelope  # echo so we can observe routing


def _passthrough_gatekeeper():
    """Real Gatekeeper lands in Phase 4.1. Until then a thin stub stands in —
    its job is to forward args verbatim so we can assert the call shape."""
    gk = MagicMock()
    gk.execute.side_effect = lambda fn, *a, **kw: fn(*a, **kw)
    return gk


def _fake_response(text="reply", tin=10, tout=20):
    return CompletionResponse(
        text=text,
        input_tokens=tin,
        output_tokens=tout,
        model="m",
        provider="anthropic",
    )


def _build_agent(provider=None, gatekeeper=None, request_timeout=None):
    if provider is None:
        provider = MagicMock()
        provider.complete = MagicMock(return_value=_fake_response())
    return _ConcreteAgent(
        agent_id="dogs",
        system_prompt="be brief",
        provider=provider,
        gatekeeper=gatekeeper or _passthrough_gatekeeper(),
        model_name="claude-haiku",
        request_timeout=request_timeout,
    )


def test_history_append_user_and_assistant():
    agent = _build_agent()
    agent._append_user("hi")
    agent._append_assistant("hello")
    assert agent.history == [
        ChatMessage(role="user", content="hi"),
        ChatMessage(role="assistant", content="hello"),
    ]


def test_generate_routes_through_gatekeeper():
    gk = _passthrough_gatekeeper()
    provider = MagicMock()
    provider.complete = MagicMock(return_value=_fake_response("woof"))
    agent = _build_agent(provider=provider, gatekeeper=gk, request_timeout=7.0)

    resp = agent.generate("Make your opening argument.")

    assert resp.text == "woof"
    gk.execute.assert_called_once()
    called_fn = gk.execute.call_args.args[0]
    assert called_fn is provider.complete
    kwargs = gk.execute.call_args.kwargs
    assert kwargs["system"] == "be brief"
    assert kwargs["model"] == "claude-haiku"
    assert kwargs["service"] == "default"
    assert kwargs["timeout"] == 7.0  # configured request_timeout forwarded to provider
    # History now has user + assistant turn.
    assert [m.role for m in agent.history] == ["user", "assistant"]
    assert agent.history[-1].content == "woof"


def test_generate_sends_full_history():
    """Each call must include the entire prior history — the LLM is stateless."""
    agent = _build_agent()
    agent.generate("turn 1")
    agent.generate("turn 2")
    # 2 calls × (user + assistant) = 4 messages on the 2nd send-list.
    second_call_messages = agent.provider.complete.call_args_list[1].kwargs["messages"]
    assert len(second_call_messages) == 3  # turn1 user, turn1 assistant, turn2 user
    assert second_call_messages[0].role == "user"
    assert second_call_messages[0].content == "turn 1"
    assert second_call_messages[-1].content == "turn 2"


def test_history_disjoint_per_instance():
    """Two agents must never share history — different processes, different state."""
    a = _build_agent()
    b = _build_agent()
    a.generate("dogs argument")
    assert len(a.history) == 2
    assert b.history == []


def test_heartbeat_emits_envelope():
    agent = _build_agent()
    out: queue.Queue = queue.Queue()
    agent.heartbeat(out, datetime(2026, 5, 21, tzinfo=timezone.utc))
    msg = out.get_nowait()
    assert isinstance(msg, Heartbeat)
    assert msg.agent_id == "dogs"


def test_run_loop_processes_until_sentinel():
    agent = _build_agent()
    inbox: queue.Queue = queue.Queue()
    outbox: queue.Queue = queue.Queue()
    inbox.put("env-1")
    inbox.put("env-2")
    inbox.put(None)  # shutdown sentinel
    agent.run(inbox, outbox)
    assert agent.received == ["env-1", "env-2"]
    assert [outbox.get_nowait() for _ in range(2)] == ["env-1", "env-2"]


def test_run_loop_reraises_on_handler_failure():
    class Boom(_ConcreteAgent):
        def receive(self, envelope):
            raise RuntimeError("kaboom")

    agent = Boom(
        agent_id="x",
        system_prompt="s",
        provider=MagicMock(),
        gatekeeper=_passthrough_gatekeeper(),
        model_name="m",
    )
    inbox: queue.Queue = queue.Queue()
    inbox.put("bad")
    with pytest.raises(RuntimeError, match="kaboom"):
        agent.run(inbox, queue.Queue())
