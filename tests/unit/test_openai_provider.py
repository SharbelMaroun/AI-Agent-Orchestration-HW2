"""OpenAIProvider tests: response normalisation + system-message prepending.

Split off from `test_llm_provider.py` for the 150-line raw cap."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from debate.shared.llm_provider.openai_provider import OpenAIProvider
from debate.shared.schemas import ChatMessage


def _msgs() -> list[ChatMessage]:
    return [
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
        ChatMessage(role="user", content="again"),
    ]


@pytest.fixture
def fake_openai_module():
    """Inject a stub `openai` module so OpenAIProvider can import it without
    requiring the optional `openai` package in the test env."""
    mod = ModuleType("openai")
    mod.OpenAI = MagicMock()
    saved = sys.modules.get("openai")
    sys.modules["openai"] = mod
    try:
        yield mod
    finally:
        if saved is None:
            del sys.modules["openai"]
        else:
            sys.modules["openai"] = saved


def _fake_response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="meow"))],
        usage=SimpleNamespace(prompt_tokens=21, completion_tokens=43),
    )


def test_openai_complete_normalizes(monkeypatch, fake_openai_module):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_response()
    fake_openai_module.OpenAI.return_value = mock_client
    resp = OpenAIProvider().complete(system="S", messages=_msgs(), model="gpt-4o-mini")
    assert resp.text == "meow"
    assert resp.input_tokens == 21
    assert resp.output_tokens == 43
    assert resp.cache_read_tokens == 0
    assert resp.provider == "openai"


def test_openai_prepends_system_message(monkeypatch, fake_openai_module):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_response()
    fake_openai_module.OpenAI.return_value = mock_client
    OpenAIProvider().complete(system="be brief", messages=_msgs(), model="gpt-4o-mini")
    sent = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent[0] == {"role": "system", "content": "be brief"}
    assert sent[1] == {"role": "user", "content": "hello"}
