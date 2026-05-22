"""OpenAI provider. Included so the LLMProvider abstraction is exercised
beyond a single vendor — making the registry / factory worth their weight.

OpenAI's chat schema folds the system prompt into the messages list (role
"system"), unlike Anthropic which takes a top-level `system` arg. We convert
on entry. OpenAI also has no native prompt-cache header; cache token fields
stay at 0 in the normalized response.
"""

from __future__ import annotations

import os

from debate.shared.llm_provider.base import LLMProvider, register
from debate.shared.schemas import ChatMessage, CompletionResponse

PROVIDER_NAME = "openai"
ENV_VAR = "OPENAI_API_KEY"


class OpenAIProvider(LLMProvider):
    """Thin wrapper around `openai.OpenAI().chat.completions.create`."""

    name = PROVIDER_NAME

    def __init__(self) -> None:
        api_key = os.environ.get(ENV_VAR)
        if not api_key:
            raise RuntimeError(f"{ENV_VAR} not set — required for provider {PROVIDER_NAME!r}")
        from openai import OpenAI  # local import keeps test mocks simple

        self._client = OpenAI(api_key=api_key)

    def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        model: str,
        max_tokens: int = 1024,
    ) -> CompletionResponse:
        api_messages: list[dict] = [{"role": "system", "content": system}]
        api_messages.extend({"role": m.role, "content": m.content} for m in messages)
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=api_messages,
        )
        return self._normalize(response, model)

    @staticmethod
    def _normalize(response: object, model: str) -> CompletionResponse:
        choice = response.choices[0]
        text = choice.message.content or ""
        usage = response.usage
        return CompletionResponse(
            text=text,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            cache_read_tokens=0,
            cache_creation_tokens=0,
            model=model,
            provider=PROVIDER_NAME,
        )


register(PROVIDER_NAME, OpenAIProvider)
