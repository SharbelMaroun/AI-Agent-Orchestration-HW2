"""Shared pytest fixtures. Helper classes + the provider-factory live in
`tests/_fixture_helpers.py` so this file stays under the raw line cap."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from debate.shared.schemas import Ping, Score
from tests._fixture_helpers import (
    HashEmbedder,
    PassthroughGatekeeper,
    make_fake_provider_factory,
)

# Re-export so existing tests doing `from tests.conftest import HashEmbedder`
# keep working without import churn.
__all__ = ["HashEmbedder", "PassthroughGatekeeper", "make_fake_provider_factory"]


@pytest.fixture
def project_root() -> Path:
    """Absolute path to the project root (where pyproject.toml lives)."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def passthrough_gatekeeper() -> PassthroughGatekeeper:
    return PassthroughGatekeeper()


@pytest.fixture
def fake_provider_factory():
    return make_fake_provider_factory()


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
