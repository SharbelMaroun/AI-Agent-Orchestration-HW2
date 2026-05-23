"""Test doubles + factories shared between the DebateAgent test files.
Filename prefix `_` so pytest does not collect it."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from debate.services.agents.debate_agent import DebateAgent
from debate.shared.schemas import CompletionResponse, Ping

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


class Dogs(DebateAgent):
    """Concrete DebateAgent subclass for tests — Dogs-side persona."""

    side = "dogs"

    def _build_search_query(self, previous_ping):
        base = "dogs better pet"
        return f"{base} study research" if previous_ping is None else f"rebut: {previous_ping.text}"


def passthrough_gk():
    gk = MagicMock()
    gk.execute.side_effect = lambda fn, *a, **kw: fn(*a, **kw)
    return gk


def agent(rag=None, search=None, llm_text='{"text": "woof", "citations": []}'):
    provider = MagicMock()
    provider.complete = MagicMock(
        return_value=CompletionResponse(
            text=llm_text,
            input_tokens=11,
            output_tokens=22,
            model="m",
            provider="anthropic",
        )
    )
    return Dogs(
        agent_id="dogs",
        system_prompt="be persuasive",
        provider=provider,
        gatekeeper=passthrough_gk(),
        model_name="m",
        rag=rag,
        search_tool=search,
    )


def opponent_ping(round_: int = 1, side: str = "cats") -> Ping:
    return Ping(round=round_, side=side, text="cats reign", timestamp=NOW)
