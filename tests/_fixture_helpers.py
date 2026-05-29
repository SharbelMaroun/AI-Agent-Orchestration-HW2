"""Test helper classes used by `conftest.py` (and a few unit tests via
direct import). Lives outside `conftest.py` so the conftest can stay
under the raw line cap."""

from __future__ import annotations

import hashlib
import re as _re
from typing import Any
from unittest.mock import MagicMock

from debate.shared.schemas import CompletionResponse


class PassthroughGatekeeper:
    """Minimal gatekeeper stand-in — runs the call directly and records it."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        self.calls.append({"service": service, "args": args, "kwargs": kwargs})
        return api_call(*args, **kwargs)


class HashEmbedder:
    """Deterministic SHA-256-based embedder — no model download, stable vectors."""

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in h[: self.dim]]

    def embed_text(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


_OPP_ROUND_RE = _re.compile(r"Opponent's previous ping \(round (\d+)")
_DEFAULT_SCORE = '{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'
_DEFAULT_VERDICT = '{"winner":"dogs","written_rationale":"clear"}'


def make_fake_provider_factory():
    """Return a `provider_factory(name)` callable producing MagicMock providers
    that respond plausibly to Dogs/Cats/Judge prompts."""

    def factory(_name: str):
        provider = MagicMock()

        def complete(*, system: str, messages: list, model: str, max_tokens: int, timeout=None):
            del system, max_tokens, timeout
            last_user = messages[-1].content if messages else ""
            low = last_user.lower()
            if "final scores" in low or "deliver the verdict" in low:
                text = _DEFAULT_VERDICT
            elif "score this ping" in low:
                text = _DEFAULT_SCORE
            else:
                m = _OPP_ROUND_RE.search(last_user)
                refers = m.group(1) if m else "null"
                text = f'{{"text":"argued","citations":[],"refers_to_ping":{refers}}}'
            return CompletionResponse(
                text=text,
                input_tokens=5,
                output_tokens=5,
                model=model,
                provider="anthropic",
            )

        provider.complete.side_effect = complete
        return provider

    return factory
