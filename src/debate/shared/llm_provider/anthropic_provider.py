"""Anthropic provider. See docs/PRD_gatekeeper.md §9a for caching rationale.

Marks the system prompt and the first user message with
`cache_control: { type: "ephemeral" }`. Per Anthropic's docs the cache covers
"everything up to and including" the marked block, so two markers (system +
first user) lets the model cache the system prompt durably and the early
history per-conversation, while later turns remain uncached and cheap.
"""

from __future__ import annotations

import os

from debate.shared.llm_provider.base import LLMProvider, register
from debate.shared.schemas import ChatMessage, CompletionResponse

PROVIDER_NAME = "anthropic"
ENV_VAR = "ANTHROPIC_API_KEY"


class AnthropicProvider(LLMProvider):
    """Thin wrapper around `anthropic.Anthropic().messages.create`."""

    name = PROVIDER_NAME

    def __init__(self) -> None:
        api_key = os.environ.get(ENV_VAR)
        if not api_key:
            raise RuntimeError(
                f"{ENV_VAR} not set — required for provider {PROVIDER_NAME!r}"
            )
        from anthropic import Anthropic  # local import keeps test mocks simple

        self._client = Anthropic(api_key=api_key)

    def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        model: str,
        max_tokens: int = 1024,
    ) -> CompletionResponse:
        api_messages = self._format_messages(messages)
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=api_messages,
        )
        return self._normalize(response, model)

    @staticmethod
    def _format_messages(messages: list[ChatMessage]) -> list[dict]:
        """First user message gets a cache_control marker; rest are plain text."""
        out: list[dict] = []
        first_user_seen = False
        for msg in messages:
            if msg.role == "user" and not first_user_seen:
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": msg.content,
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                    }
                )
                first_user_seen = True
            else:
                out.append({"role": msg.role, "content": msg.content})
        return out

    @staticmethod
    def _normalize(response: object, model: str) -> CompletionResponse:
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = response.usage
        return CompletionResponse(
            text=text,
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            model=model,
            provider=PROVIDER_NAME,
        )


register(PROVIDER_NAME, AnthropicProvider)
