"""LLM provider registry + the registry-level guarantees.

Anthropic-specific tests live in `test_anthropic_provider.py`; OpenAI
in `test_openai_provider.py`. Split for the 150-line raw cap."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from debate.shared.llm_provider import build_provider, known_providers, register
from debate.shared.llm_provider.anthropic_provider import AnthropicProvider
from debate.shared.llm_provider.base import LLMProvider
from debate.shared.llm_provider.openai_provider import OpenAIProvider


def test_registry_known_providers():
    names = known_providers()
    assert "anthropic" in names
    assert "openai" in names
    assert "google" in names


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


def test_build_provider_returns_instance(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("anthropic.Anthropic"):
        provider = build_provider("anthropic")
    assert isinstance(provider, AnthropicProvider)
