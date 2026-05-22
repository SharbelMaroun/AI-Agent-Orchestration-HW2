"""DebateAgent tests (Phase 3.5)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from debate.services.agents.debate_agent import (
    ClashViolationError,
    DebateAgent,
    PingParseError,
)
from debate.shared.schemas import CompletionResponse, OpeningBrief, Ping, YourTurn

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


class _Dogs(DebateAgent):
    side = "dogs"

    def _build_search_query(self, previous_ping):
        base = "dogs better pet"
        return f"{base} study research" if previous_ping is None else f"rebut: {previous_ping.text}"


def _passthrough_gk():
    gk = MagicMock()
    gk.execute.side_effect = lambda fn, *a, **kw: fn(*a, **kw)
    return gk


def _agent(rag=None, search=None, llm_text='{"text": "woof", "citations": []}'):
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
    return _Dogs(
        agent_id="dogs",
        system_prompt="be persuasive",
        provider=provider,
        gatekeeper=_passthrough_gk(),
        model_name="m",
        rag=rag,
        search_tool=search,
    )


def _opponent_ping(round_=1, side="cats"):
    return Ping(round=round_, side=side, text="cats reign", timestamp=NOW)


def test_collect_evidence_calls_both_tools():
    rag = MagicMock()
    rag.retrieve.return_value = ["passage-1"]
    search = MagicMock()
    search.search.return_value = [{"title": "t"}]
    agent = _agent(rag=rag, search=search)
    ev = agent._collect_evidence("dogs research")
    rag.retrieve.assert_called_once_with("dogs research", k=3)
    search.search.assert_called_once_with("dogs research", max_results=5)
    assert ev == {"search": [{"title": "t"}], "rag": ["passage-1"]}


def test_collect_evidence_works_without_tools():
    agent = _agent()
    assert agent._collect_evidence("anything") == {"search": [], "rag": []}


def test_parse_ping_valid_json():
    text = 'Sure. {"text": "loyal companions", "citations": ["url"]}'
    ping = DebateAgent._parse_ping_json(text, side="dogs", round_=1)
    assert ping.text == "loyal companions"
    assert ping.side == "dogs"
    assert ping.round == 1


def test_parse_ping_invalid_json_raises():
    with pytest.raises(PingParseError):
        DebateAgent._parse_ping_json("no JSON here", side="dogs", round_=1)


def test_parse_ping_bad_schema_raises():
    with pytest.raises(PingParseError):
        DebateAgent._parse_ping_json(
            '{"text": 123, "round": "not-a-number"}', side="dogs", round_=1
        )


def test_clash_round_one_no_validation():
    ping = Ping(round=1, side="dogs", text="open", timestamp=NOW)
    DebateAgent._validate_clash(ping, previous_ping=None)  # no raise


def test_clash_missing_reference_raises():
    ping = Ping(round=2, side="dogs", text="x", timestamp=NOW, refers_to_ping=None)
    with pytest.raises(ClashViolationError):
        DebateAgent._validate_clash(ping, _opponent_ping(round_=1))


def test_clash_wrong_reference_raises():
    ping = Ping(round=3, side="dogs", text="x", timestamp=NOW, refers_to_ping=99)
    with pytest.raises(ClashViolationError):
        DebateAgent._validate_clash(ping, _opponent_ping(round_=2))


def test_clash_correct_reference_passes():
    ping = Ping(round=2, side="dogs", text="x", timestamp=NOW, refers_to_ping=1)
    DebateAgent._validate_clash(ping, _opponent_ping(round_=1))


def test_handle_your_turn_round1_full_flow():
    rag = MagicMock()
    rag.retrieve.return_value = []
    search = MagicMock()
    search.search.return_value = []
    agent = _agent(
        rag=rag,
        search=search,
        llm_text='{"text": "dogs win", "citations": []}',
    )
    ping = agent.handle_your_turn(YourTurn(round=1, previous_ping=None))
    assert ping.text == "dogs win"
    assert ping.side == "dogs"
    assert ping.tokens_in == 11
    assert ping.tokens_out == 22
    search.search.assert_called_once()  # query had no opponent ping yet


def test_handle_your_turn_round2_validates_clash():
    agent = _agent(
        llm_text='{"text": "rebuttal", "refers_to_ping": 1, "citations": []}',
    )
    opp = _opponent_ping(round_=1)
    ping = agent.handle_your_turn(YourTurn(round=2, previous_ping=opp))
    assert ping.refers_to_ping == 1


def test_handle_your_turn_round2_missing_refers_to_ping_auto_fills():
    """Smaller models sometimes omit `refers_to_ping`. We fill it in from
    the envelope context — the Judge's `clash` dimension separately scores
    whether the ping *rhetorically* engaged the opponent."""
    agent = _agent(llm_text='{"text": "no clash here", "citations": []}')
    opp = _opponent_ping(round_=1)
    ping = agent.handle_your_turn(YourTurn(round=2, previous_ping=opp))
    assert ping.refers_to_ping == 1


def test_handle_your_turn_wrong_refers_to_ping_still_raises():
    """If the model returns the *wrong* round number, that's a real clash
    violation — not just a missing field — and must still raise."""
    agent = _agent(
        llm_text='{"text": "bad", "citations": [], "refers_to_ping": 99}'
    )
    opp = _opponent_ping(round_=1)
    with pytest.raises(ClashViolationError):
        agent.handle_your_turn(YourTurn(round=2, previous_ping=opp))


def test_receive_opening_brief_stashes_it():
    agent = _agent()
    brief = OpeningBrief(topic="t", num_rounds=10, rules="r", side="dogs")
    assert agent.receive(brief) is None
    assert agent.opening_brief is brief


def test_receive_your_turn_returns_ping():
    agent = _agent(llm_text='{"text": "go", "citations": []}')
    out = agent.receive(YourTurn(round=1, previous_ping=None))
    assert isinstance(out, Ping)


def test_receive_unknown_envelope_returns_none():
    agent = _agent()
    assert agent.receive("garbage") is None
