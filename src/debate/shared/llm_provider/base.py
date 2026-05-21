"""LLMProvider ABC + provider registry. Phase 3.3."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, system: str, messages: list, model: str, max_tokens: int = 1024) -> object:
        """Return a CompletionResponse. Phase 3.3."""


def build_provider(name: str) -> LLMProvider:
    """Factory: name → concrete LLMProvider instance. Phase 3.3."""
    raise NotImplementedError
