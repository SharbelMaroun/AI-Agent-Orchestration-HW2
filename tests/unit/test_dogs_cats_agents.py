"""DogsAgent + CatsAgent tests (Phases 3.6 + 3.7)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from debate.services.agents.cats_agent import CatsAgent
from debate.services.agents.dogs_agent import DogsAgent
from debate.shared.schemas import CompletionResponse


def _passthrough_gk():
    gk = MagicMock()
    gk.execute.side_effect = lambda fn, *a, **kw: fn(*a, **kw)
    return gk


def _provider():
    p = MagicMock()
    p.complete = MagicMock(
        return_value=CompletionResponse(
            text='{"text":"x","citations":[]}',
            input_tokens=1,
            output_tokens=1,
            model="m",
            provider="anthropic",
        )
    )
    return p


def test_dogs_loads_default_prompt_file():
    agent = DogsAgent(
        provider=_provider(),
        gatekeeper=_passthrough_gk(),
        model_name="m",
    )
    assert agent.side == "dogs"
    assert agent.agent_id == "dogs"
    assert "Dogs Advocate" in agent.system_prompt
    assert agent.rag_collection == "dogs"


def test_cats_loads_default_prompt_file():
    agent = CatsAgent(
        provider=_provider(),
        gatekeeper=_passthrough_gk(),
        model_name="m",
    )
    assert agent.side == "cats"
    assert agent.agent_id == "cats"
    assert "Cats Advocate" in agent.system_prompt
    assert agent.rag_collection == "cats"


def test_dogs_accepts_inline_prompt_override():
    agent = DogsAgent(
        provider=_provider(),
        gatekeeper=_passthrough_gk(),
        model_name="m",
        system_prompt="custom dogs",
    )
    assert agent.system_prompt == "custom dogs"


def test_cats_accepts_inline_prompt_override():
    agent = CatsAgent(
        provider=_provider(),
        gatekeeper=_passthrough_gk(),
        model_name="m",
        system_prompt="custom cats",
    )
    assert agent.system_prompt == "custom cats"


def test_dogs_round1_query_has_authority_keywords():
    agent = DogsAgent(
        provider=_provider(),
        gatekeeper=_passthrough_gk(),
        model_name="m",
    )
    q = agent._build_search_query(previous_ping=None)
    assert "study" in q and "research" in q


def test_cats_round1_query_has_literary_keywords():
    agent = CatsAgent(
        provider=_provider(),
        gatekeeper=_passthrough_gk(),
        model_name="m",
    )
    q = agent._build_search_query(previous_ping=None)
    assert "literature" in q and "philosophy" in q


def test_skill_files_exist_on_disk():
    """Guard against the skills/ directory being deleted accidentally."""
    assert Path("skills/dogs/SKILL.md").exists()
    assert Path("skills/cats/SKILL.md").exists()
    assert Path("skills/judge/SKILL.md").exists()
