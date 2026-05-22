"""Unit tests for debate.shared.llm_provider.google_provider.

The `google.generativeai` package is heavy and network-touching; tests
inject a fake `genai` module into `sys.modules` before constructing the
provider so no real client is created.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from debate.shared.llm_provider import build_provider, known_providers
from debate.shared.llm_provider.google_provider import GoogleProvider
from debate.shared.schemas import ChatMessage


def _install_fake_genai(monkeypatch, fake_response: object) -> MagicMock:
    """Replace `google.generativeai` with a fake module returning `fake_response`."""
    fake_module = ModuleType("google.generativeai")
    fake_module.configure = MagicMock()
    model_instance = MagicMock()
    model_instance.generate_content.return_value = fake_response
    fake_module.GenerativeModel = MagicMock(return_value=model_instance)
    # google.generativeai imports as `google.generativeai`, so the parent
    # package needs to exist too.
    google_pkg = ModuleType("google")
    google_pkg.generativeai = fake_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_module)
    return fake_module


def _fake_response(text: str = "argued") -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=11,
            candidates_token_count=7,
            cached_content_token_count=3,
        ),
    )


def test_google_in_known_providers() -> None:
    assert "google" in known_providers()


def test_google_missing_env_raises(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        GoogleProvider()


def test_google_complete_normalizes(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    _install_fake_genai(monkeypatch, _fake_response("hello-world"))
    p = GoogleProvider()
    resp = p.complete(
        system="you are a helpful debater",
        messages=[
            ChatMessage(role="user", content="hi"),
            ChatMessage(role="assistant", content="hello"),
            ChatMessage(role="user", content="again"),
        ],
        model="gemini-2.5-flash",
        max_tokens=128,
    )
    assert resp.text == "hello-world"
    assert resp.input_tokens == 11
    assert resp.output_tokens == 7
    assert resp.cache_read_tokens == 3
    assert resp.cache_creation_tokens == 0
    assert resp.model == "gemini-2.5-flash"
    assert resp.provider == "google"


def test_google_role_translation(monkeypatch) -> None:
    """Gemini uses 'model' rather than 'assistant'."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    fake = _install_fake_genai(monkeypatch, _fake_response())
    p = GoogleProvider()
    p.complete(
        system="sys",
        messages=[
            ChatMessage(role="user", content="A"),
            ChatMessage(role="assistant", content="B"),
        ],
        model="gemini-2.5-flash",
    )
    model_instance = fake.GenerativeModel.return_value
    sent_contents = model_instance.generate_content.call_args[0][0]
    roles = [c["role"] for c in sent_contents]
    assert roles == ["user", "model"]


def test_google_system_instruction_passed(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    fake = _install_fake_genai(monkeypatch, _fake_response())
    p = GoogleProvider()
    p.complete(
        system="you are wise", messages=[ChatMessage(role="user", content="?")],
        model="gemini-2.5-flash",
    )
    call_kwargs = fake.GenerativeModel.call_args.kwargs
    assert call_kwargs["system_instruction"] == "you are wise"
    assert call_kwargs["model_name"] == "gemini-2.5-flash"


def test_build_provider_returns_google(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    _install_fake_genai(monkeypatch, _fake_response())
    p = build_provider("google")
    assert isinstance(p, GoogleProvider)


def test_google_handles_missing_usage_metadata(monkeypatch) -> None:
    """Gemini may omit usage_metadata on error paths — we must not crash."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    bare = SimpleNamespace(text="ok", usage_metadata=None)
    _install_fake_genai(monkeypatch, bare)
    p = GoogleProvider()
    resp = p.complete(system="s", messages=[ChatMessage(role="user", content="x")],
                      model="gemini-2.5-flash")
    assert resp.input_tokens == 0
    assert resp.output_tokens == 0
