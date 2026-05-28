"""`handle_your_turn` + `receive` integration tests for DebateAgent.

Pure-helper tests (collect_evidence, parse_ping, clash validation) live
in `test_debate_agent.py`. Shared doubles in `_debate_agent_test_helpers`."""

from __future__ import annotations

from unittest.mock import MagicMock

from debate.shared.schemas import CompletionResponse, OpeningBrief, Ping, YourTurn
from tests.unit._debate_agent_test_helpers import agent, opponent_ping


def test_handle_your_turn_round1_full_flow():
    rag = MagicMock()
    rag.retrieve.return_value = []
    search = MagicMock()
    search.search.return_value = []
    a = agent(
        rag=rag,
        search=search,
        llm_text='{"text": "dogs win", "citations": []}',
    )
    ping = a.handle_your_turn(YourTurn(round=1, previous_ping=None))
    assert ping.text == "dogs win"
    assert ping.side == "dogs"
    assert ping.tokens_in == 11
    assert ping.tokens_out == 22
    search.search.assert_called_once()


def test_handle_your_turn_round2_validates_clash():
    a = agent(llm_text='{"text": "rebuttal", "refers_to_ping": 1, "citations": []}')
    ping = a.handle_your_turn(YourTurn(round=2, previous_ping=opponent_ping(round_=1)))
    assert ping.refers_to_ping == 1


def test_handle_your_turn_round2_missing_refers_to_ping_auto_fills():
    """Smaller models sometimes omit `refers_to_ping`. We fill it in from
    the envelope context — the Judge's `clash` dimension separately scores
    whether the ping *rhetorically* engaged the opponent."""
    a = agent(llm_text='{"text": "no clash here", "citations": []}')
    ping = a.handle_your_turn(YourTurn(round=2, previous_ping=opponent_ping(round_=1)))
    assert ping.refers_to_ping == 1


def test_handle_your_turn_repairs_non_json_reply_once():
    a = agent(llm_text="not json")
    a.provider.complete.side_effect = [
        CompletionResponse(
            text="cats are graceful, but dogs help people",
            input_tokens=11,
            output_tokens=22,
            model="m",
            provider="anthropic",
        ),
        CompletionResponse(
            text='{"text": "repaired argument", "citations": []}',
            input_tokens=7,
            output_tokens=8,
            model="m",
            provider="anthropic",
        ),
    ]
    ping = a.handle_your_turn(YourTurn(round=1, previous_ping=None))
    assert ping.text == "repaired argument"
    assert ping.tokens_in == 18
    assert ping.tokens_out == 30


def test_handle_your_turn_wraps_failed_repair_as_ping():
    a = agent(llm_text="not json")
    a.provider.complete.side_effect = [
        CompletionResponse(
            text="first prose answer",
            input_tokens=11,
            output_tokens=22,
            model="m",
            provider="anthropic",
        ),
        CompletionResponse(
            text="still prose, but usable as an argument",
            input_tokens=7,
            output_tokens=8,
            model="m",
            provider="anthropic",
        ),
    ]
    ping = a.handle_your_turn(YourTurn(round=2, previous_ping=opponent_ping(round_=1)))
    assert ping.text == "still prose, but usable as an argument"
    assert ping.refers_to_ping == 1


def test_handle_your_turn_wrong_refers_to_ping_is_autocorrected():
    """Off-by-one hallucinations (e.g. model returns 8 in round 10 instead
    of 9) used to abort the whole debate. Since 2026-05-28 the agent silently
    overwrites any non-matching `refers_to_ping` with envelope.previous_ping.round;
    the structural field is unambiguous from envelope context, and the Judge's
    `clash` dimension separately scores rhetorical engagement."""
    a = agent(llm_text='{"text": "bad", "citations": [], "refers_to_ping": 99}')
    ping = a.handle_your_turn(YourTurn(round=2, previous_ping=opponent_ping(round_=1)))
    assert ping.refers_to_ping == 1


def test_receive_opening_brief_stashes_it():
    a = agent()
    brief = OpeningBrief(topic="t", num_rounds=10, rules="r", side="dogs")
    assert a.receive(brief) is None
    assert a.opening_brief is brief


def test_receive_your_turn_returns_ping():
    a = agent(llm_text='{"text": "go", "citations": []}')
    out = a.receive(YourTurn(round=1, previous_ping=None))
    assert isinstance(out, Ping)


def test_receive_unknown_envelope_returns_none():
    assert agent().receive("garbage") is None
