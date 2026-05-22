"""LLMProvider ABC + provider registry. See docs/PLAN.md ADR-009.

The registry decouples agent code from concrete SDK choice — agents take a
provider name from `config/setup.json` and call `build_provider(name)`.
Adding a new provider is a single `register("name", cls)` call, no agent code
changes. This keeps the abstraction thin (no LangChain-style routing layer)
while still satisfying the "Gatekeeper is the single chokepoint" rule: every
concrete provider returns a normalized `CompletionResponse` which the
Gatekeeper can then meter uniformly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from debate.shared.schemas import ChatMessage, CompletionResponse


class LLMProvider(ABC):
    """One concrete provider per LLM vendor (Anthropic, OpenAI, ...)."""

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        model: str,
        max_tokens: int = 1024,
    ) -> CompletionResponse:
        """Send a single completion request. Must normalize vendor response."""


_REGISTRY: dict[str, type[LLMProvider]] = {}


def register(name: str, cls: type[LLMProvider]) -> None:
    """Register a provider class under `name`. Idempotent on identical class."""
    existing = _REGISTRY.get(name)
    if existing is not None and existing is not cls:
        raise ValueError(f"Provider {name!r} already registered to {existing.__name__}")
    _REGISTRY[name] = cls


def build_provider(name: str) -> LLMProvider:
    """Look up `name` in the registry and instantiate the provider."""
    if name not in _REGISTRY:
        raise ValueError(f"Unknown LLM provider {name!r}. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def known_providers() -> list[str]:
    """Helper for diagnostics / config validation."""
    return sorted(_REGISTRY)
