"""DebateAgent core tests: evidence collection + JSON parse + clash validation.

`handle_your_turn` and `receive` integration tests live in
`test_debate_agent_turn.py`. Shared test doubles in
`_debate_agent_test_helpers.py`. Split for the 150-line raw cap."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from debate.services.agents.debate_agent import (
    ClashViolationError,
    DebateAgent,
    PingParseError,
)
from debate.shared.schemas import Ping
from tests.unit._debate_agent_test_helpers import NOW, agent, opponent_ping


def test_collect_evidence_calls_both_tools():
    rag = MagicMock()
    rag.retrieve.return_value = ["passage-1"]
    search = MagicMock()
    search.search.return_value = [{"title": "t"}]
    a = agent(rag=rag, search=search)
    ev = a._collect_evidence("dogs research")
    rag.retrieve.assert_called_once_with("dogs research", k=3)
    search.search.assert_called_once_with("dogs research", max_results=5)
    assert ev["search"] == [{"title": "t"}]
    assert ev["rag"] == ["passage-1"]
    assert len(ev["research_cards"]) == 3


def test_collect_evidence_works_without_tools():
    a = agent()
    ev = a._collect_evidence("anything")
    assert ev["search"] == []
    assert ev["rag"] == []
    assert len(ev["research_cards"]) == 3


def test_build_user_prompt_includes_research_cards():
    a = agent()
    evidence = {
        "search": [],
        "rag": [],
        "research_cards": [{"assistant": "DogsHealthResearcher", "claim": "health"}],
    }
    prompt = a._build_user_prompt(None, evidence, 1)
    assert "Research assistant cards" in prompt
    assert "DogsHealthResearcher" in prompt


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
            '{"text": 123, "round": "not-a-number"}',
            side="dogs",
            round_=1,
        )


def test_clash_round_one_no_validation():
    ping = Ping(round=1, side="dogs", text="open", timestamp=NOW)
    DebateAgent._validate_clash(ping, previous_ping=None)  # no raise


def test_clash_missing_reference_raises():
    ping = Ping(round=2, side="dogs", text="x", timestamp=NOW, refers_to_ping=None)
    with pytest.raises(ClashViolationError):
        DebateAgent._validate_clash(ping, opponent_ping(round_=1))


def test_clash_wrong_reference_raises():
    ping = Ping(round=3, side="dogs", text="x", timestamp=NOW, refers_to_ping=99)
    with pytest.raises(ClashViolationError):
        DebateAgent._validate_clash(ping, opponent_ping(round_=2))


def test_clash_correct_reference_passes():
    ping = Ping(round=2, side="dogs", text="x", timestamp=NOW, refers_to_ping=1)
    DebateAgent._validate_clash(ping, opponent_ping(round_=1))
