"""Google Gemini provider.

Gemini's REST API doesn't separate the system prompt from user/assistant
turns the same way Anthropic does — the SDK accepts it via the model's
`system_instruction` argument. We pass it there and let the conversation
history map directly to `Content` objects.

Gemini does not expose cache-read/cache-creation token counts in the same
shape as Anthropic, so those fields stay at 0 — the Gatekeeper's cost
math still works (the cache-multiplier terms simply contribute 0).
"""

from __future__ import annotations

import os

from debate.shared.llm_provider.base import LLMProvider, register
from debate.shared.schemas import ChatMessage, CompletionResponse

PROVIDER_NAME = "google"
ENV_VAR = "GOOGLE_API_KEY"


class GoogleProvider(LLMProvider):
    """Wrapper around `google.generativeai.GenerativeModel.generate_content`."""

    name = PROVIDER_NAME

    def __init__(self) -> None:
        api_key = os.environ.get(ENV_VAR)
        if not api_key:
            raise RuntimeError(
                f"{ENV_VAR} not set — required for provider {PROVIDER_NAME!r}"
            )
        import google.generativeai as genai  # local import keeps test mocks simple

        genai.configure(api_key=api_key)
        self._genai = genai

    def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        model: str,
        max_tokens: int = 1024,
    ) -> CompletionResponse:
        contents = self._format_messages(messages)
        client = self._genai.GenerativeModel(model_name=model, system_instruction=system)
        response = client.generate_content(
            contents,
            generation_config={"max_output_tokens": max_tokens},
        )
        return self._normalize(response, model)

    @staticmethod
    def _format_messages(messages: list[ChatMessage]) -> list[dict]:
        """Gemini uses 'user' and 'model' roles (not 'assistant')."""
        out: list[dict] = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            out.append({"role": role, "parts": [{"text": msg.content}]})
        return out

    @staticmethod
    def _normalize(response: object, model: str) -> CompletionResponse:
        text = getattr(response, "text", "") or ""
        usage = getattr(response, "usage_metadata", None)
        return CompletionResponse(
            text=text,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            cache_read_tokens=getattr(usage, "cached_content_token_count", 0) or 0,
            cache_creation_tokens=0,
            model=model,
            provider=PROVIDER_NAME,
        )


register(PROVIDER_NAME, GoogleProvider)
