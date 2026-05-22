"""Shared pytest fixtures.

The factories here exist to make integration-style tests (and any unit test
that needs a multi-agent setup) one-liners. Each fixture is named after the
collaborator it provides so the test signature reads like a wiring diagram.
"""

from __future__ import annotations

import hashlib
import re as _re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from debate.shared.schemas import CompletionResponse, Ping, Score


@pytest.fixture
def project_root() -> Path:
    """Absolute path to the project root (where pyproject.toml lives)."""
    return Path(__file__).resolve().parent.parent


class PassthroughGatekeeper:
    """Minimal gatekeeper stand-in — runs the call directly and records it."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        self.calls.append({"service": service, "args": args, "kwargs": kwargs})
        return api_call(*args, **kwargs)


@pytest.fixture
def passthrough_gatekeeper() -> PassthroughGatekeeper:
    return PassthroughGatekeeper()


_OPP_ROUND_RE = _re.compile(r"Opponent's previous ping \(round (\d+)")


def make_fake_provider_factory():
    """Return a `provider_factory(name)` callable producing MagicMock providers
    that respond plausibly to Dogs/Cats/Judge prompts.

    The same canned-response logic the original SDK test used, lifted here so
    every full-debate test gets it for free.
    """
    default_score = '{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'
    default_verdict = '{"winner":"dogs","written_rationale":"clear"}'

    def factory(_name: str):
        provider = MagicMock()

        def complete(*, system: str, messages: list, model: str, max_tokens: int):
            del system, max_tokens
            last_user = messages[-1].content if messages else ""
            low = last_user.lower()
            if "final scores" in low or "deliver the verdict" in low:
                text = default_verdict
            elif "score this ping" in low:
                text = default_score
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


@pytest.fixture
def fake_provider_factory():
    return make_fake_provider_factory()


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


@pytest.fixture
def hash_embedder() -> HashEmbedder:
    return HashEmbedder()


@pytest.fixture
def sample_ping_factory():
    """Return a factory: `make_ping(round=1, side="dogs", **kw) -> Ping`."""

    def make(round: int = 1, side: str = "dogs", text: str = "argued", **kw: Any) -> Ping:
        defaults: dict[str, Any] = {
            "round": round,
            "side": side,
            "text": text,
            "citations": [],
            "refers_to_ping": None,
            "timestamp": datetime.now(timezone.utc),
            "tokens_in": 5,
            "tokens_out": 5,
        }
        defaults.update(kw)
        return Ping(**defaults)

    return make


@pytest.fixture
def sample_score_factory():
    """Return a factory: `make_score(ping_round=1, side="dogs", **kw) -> Score`."""

    def make(ping_round: int = 1, side: str = "dogs", **kw: Any) -> Score:
        defaults: dict[str, Any] = {
            "ping_round": ping_round,
            "side": side,
            "structure": 2,
            "logos": 2,
            "pathos": 2,
            "ethos": 2,
            "clash": 2,
            "rationale": "ok",
        }
        defaults.update(kw)
        return Score(**defaults)

    return make
