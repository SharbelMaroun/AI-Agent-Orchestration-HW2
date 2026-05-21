"""Anthropic provider implementation. Phase 3.3."""

from debate.shared.llm_provider.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Wraps the official `anthropic` SDK. Phase 3.3."""

    def complete(self, system: str, messages: list, model: str, max_tokens: int = 1024) -> object:
        """Call anthropic.messages.create and normalize the response. Phase 3.3."""
        raise NotImplementedError
