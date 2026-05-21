"""LLM provider registry + concrete provider tests (Phase 3.3).

External SDKs are mocked. We never touch the network and never require a real
API key — the test that requires the env var asserts the *absence* path.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from debate.shared.llm_provider import build_provider, known_providers, register
from debate.shared.llm_provider.anthropic_provider import AnthropicProvider
from debate.shared.llm_provider.base import LLMProvider
from debate.shared.llm_provider.openai_provider import OpenAIProvider
from debate.shared.schemas import ChatMessage


def _msgs() -> list[ChatMessage]:
    return [
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
        ChatMessage(role="user", content="again"),
    ]


def test_registry_known_providers():
    names = known_providers()
    assert "anthropic" in names
    assert "openai" in names


def test_registry_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_provider("does-not-exist")


def test_register_rejects_conflicting_class():
    class Fake(LLMProvider):
        def complete(self, system, messages, model, max_tokens=1024):
            raise NotImplementedError

    with pytest.raises(ValueError, match="already registered"):
        register("anthropic", Fake)


def test_register_idempotent_same_class():
    register("anthropic", AnthropicProvider)  # no raise


def test_anthropic_missing_env_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()


def test_openai_missing_env_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIProvider()


def _fake_anthropic_response():
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="woof")],
        usage=SimpleNamespace(
            input_tokens=12,
            output_tokens=34,
            cache_read_input_tokens=5,
            cache_creation_input_tokens=7,
        ),
    )


def test_anthropic_complete_normalizes(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_anthropic_response()
        mock_cls.return_value = mock_client

        provider = AnthropicProvider()
        resp = provider.complete(
            system="be brief", messages=_msgs(), model="claude-haiku-4-5-20251001"
        )

    assert resp.text == "woof"
    assert resp.input_tokens == 12
    assert resp.output_tokens == 34
    assert resp.cache_read_tokens == 5
    assert resp.cache_creation_tokens == 7
    assert resp.provider == "anthropic"
    assert resp.model == "claude-haiku-4-5-20251001"


def test_anthropic_marks_cache_on_system_and_first_user(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _fake_anthropic_response()
        mock_cls.return_value = mock_client

        AnthropicProvider().complete(
            system="S", messages=_msgs(), model="claude-haiku-4-5-20251001"
        )

    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    first_user = kwargs["messages"][0]
    assert first_user["role"] == "user"
    assert first_user["content"][0]["cache_control"] == {"type": "ephemeral"}
    # Second user message must NOT carry cache_control (cheap later turns).
    second_user = kwargs["messages"][2]
    assert second_user["role"] == "user"
    assert isinstance(second_user["content"], str)


@pytest.fixture
def fake_openai_module():
    """Inject a stub `openai` module so OpenAIProvider can import it without
    requiring the optional `openai` package to be installed in the test env."""
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


def _fake_openai_response():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="meow"))],
        usage=SimpleNamespace(prompt_tokens=21, completion_tokens=43),
    )


def test_openai_complete_normalizes(monkeypatch, fake_openai_module):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_openai_response()
    fake_openai_module.OpenAI.return_value = mock_client

    provider = OpenAIProvider()
    resp = provider.complete(system="S", messages=_msgs(), model="gpt-4o-mini")

    assert resp.text == "meow"
    assert resp.input_tokens == 21
    assert resp.output_tokens == 43
    assert resp.cache_read_tokens == 0
    assert resp.provider == "openai"


def test_openai_prepends_system_message(monkeypatch, fake_openai_module):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_openai_response()
    fake_openai_module.OpenAI.return_value = mock_client

    OpenAIProvider().complete(system="be brief", messages=_msgs(), model="gpt-4o-mini")

    sent = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent[0] == {"role": "system", "content": "be brief"}
    assert sent[1] == {"role": "user", "content": "hello"}


def test_build_provider_returns_instance(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("anthropic.Anthropic"):
        provider = build_provider("anthropic")
    assert isinstance(provider, AnthropicProvider)
