"""AnthropicProvider tests: response normalisation + prompt-caching markers.

Split off from `test_llm_provider.py` for the 150-line raw cap."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from debate.shared.llm_provider.anthropic_provider import AnthropicProvider
from debate.shared.schemas import ChatMessage


def _msgs() -> list[ChatMessage]:
    return [
        ChatMessage(role="user", content="hello"),
        ChatMessage(role="assistant", content="hi"),
        ChatMessage(role="user", content="again"),
    ]


def _fake_response():
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
        mock_client.messages.create.return_value = _fake_response()
        mock_cls.return_value = mock_client
        resp = AnthropicProvider().complete(
            system="be brief",
            messages=_msgs(),
            model="claude-haiku-4-5-20251001",
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
        mock_client.messages.create.return_value = _fake_response()
        mock_cls.return_value = mock_client
        AnthropicProvider().complete(
            system="S",
            messages=_msgs(),
            model="claude-haiku-4-5-20251001",
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
