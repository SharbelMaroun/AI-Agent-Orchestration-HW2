"""OpenAI provider implementation. Phase 3.3.

Optional — only used if a `provider: "openai"` is set in config/setup.json.
"""

from debate.shared.llm_provider.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Wraps the official `openai` SDK. Phase 3.3."""

    def complete(self, system: str, messages: list, model: str, max_tokens: int = 1024) -> object:
        """Call openai.chat.completions.create and normalize the response. Phase 3.3."""
        raise NotImplementedError
