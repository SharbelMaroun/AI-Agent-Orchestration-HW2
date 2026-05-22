"""Unit tests for debate.services.rag.embedder.

The real sentence-transformers download is ~80MB and slow; tests substitute a
deterministic fake model via the `_load_model` hook.
"""

from __future__ import annotations

from typing import Any

import pytest

from debate.services.rag.embedder import Embedder


class FakeST:
    """Minimal stand-in for SentenceTransformer."""

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self.calls = 0

    def encode(self, texts: list[str], **_kw: Any) -> list[list[float]]:
        self.calls += 1
        return [[float(len(t) + i) for i in range(self.dim)] for t in texts]


class FakeEmbedder(Embedder):
    """Skip the real model load; expose the fake for assertions."""

    def __init__(self, dim: int = 8, model_name: str = "fake") -> None:
        super().__init__(model_name=model_name)
        self._fake = FakeST(dim=dim)

    def _load_model(self) -> Any:
        return self._fake


@pytest.fixture(autouse=True)
def _clear_cache():
    yield
    Embedder._cache.clear()


def test_embed_text_returns_vector() -> None:
    e = FakeEmbedder(dim=4)
    out = e.embed_text("hello")
    assert isinstance(out, list)
    assert len(out) == 4
    assert all(isinstance(x, float) for x in out)


def test_embed_batch_matches_singles() -> None:
    e = FakeEmbedder(dim=3)
    batch = e.embed_batch(["a", "bb", "ccc"])
    assert len(batch) == 3
    # Same content via embed_text path produces identical vectors.
    e2 = FakeEmbedder(dim=3)
    assert e2.embed_text("bb") == batch[1]


def test_embed_batch_empty_returns_empty() -> None:
    e = FakeEmbedder()
    assert e.embed_batch([]) == []


def test_dim_probes_with_one_call() -> None:
    e = FakeEmbedder(dim=5)
    assert e.dim() == 5


def test_model_cached_at_class_level() -> None:
    # Two Embedder instances with the same model_name reuse the cached object.
    Embedder._cache.clear()
    sentinel = object()
    Embedder._cache["shared"] = sentinel
    a = Embedder("shared")
    b = Embedder("shared")
    assert a.model is sentinel
    assert b.model is sentinel
