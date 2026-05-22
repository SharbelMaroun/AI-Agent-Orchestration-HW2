"""Unit tests for debate.services.rag.rag_store.

Uses a deterministic hash-based fake embedder so tests don't need
sentence-transformers, but exercises the real ChromaDB persistent client.
"""

from __future__ import annotations

import hashlib

import pytest

from debate.services.rag.rag_store import Passage, RAGStore


class HashEmbedder:
    """Stable, repeatable embeddings derived from a SHA-256 of the text."""

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
def store(tmp_path):
    return RAGStore(
        collection_name="test_col", persist_dir=tmp_path / "chroma", embedder=HashEmbedder()
    )


def test_add_then_retrieve(store: RAGStore) -> None:
    added = store.add(
        documents=["dogs love walks", "cats love windows"],
        metadatas=[{"side": "dogs"}, {"side": "cats"}],
        ids=["d1", "c1"],
    )
    assert added == 2
    assert store.count() == 2
    out = store.retrieve("dogs love walks", k=1)
    assert len(out) == 1
    assert isinstance(out[0], Passage)
    assert out[0].text == "dogs love walks"
    assert out[0].metadata["side"] == "dogs"


def test_retrieve_k_results(store: RAGStore) -> None:
    docs = [f"text {i}" for i in range(5)]
    store.add(docs, [{"i": i} for i in range(5)], [f"id-{i}" for i in range(5)])
    out = store.retrieve("text 0", k=3)
    assert len(out) == 3


def test_retrieve_empty_returns_empty(store: RAGStore) -> None:
    assert store.retrieve("anything") == []


def test_retrieve_empty_query_returns_empty(store: RAGStore) -> None:
    store.add(["x"], [{}], ["id"])
    assert store.retrieve("   ", k=1) == []


def test_add_is_idempotent(store: RAGStore) -> None:
    store.add(["foo"], [{}], ["id-1"])
    again = store.add(["foo"], [{}], ["id-1"])
    assert again == 0
    assert store.count() == 1


def test_add_partial_overlap_inserts_only_new(store: RAGStore) -> None:
    store.add(["a"], [{}], ["a"])
    n = store.add(["a", "b", "c"], [{}, {}, {}], ["a", "b", "c"])
    assert n == 2
    assert store.count() == 3


def test_isolated_per_collection(tmp_path) -> None:
    a = RAGStore("col_a", tmp_path / "chroma", HashEmbedder())
    b = RAGStore("col_b", tmp_path / "chroma", HashEmbedder())
    a.add(["dogs"], [{}], ["x"])
    assert a.count() == 1
    assert b.count() == 0


def test_persistence_across_reload(tmp_path) -> None:
    s1 = RAGStore("col_p", tmp_path / "chroma", HashEmbedder())
    s1.add(["dog content"], [{"side": "dogs"}], ["p1"])
    s2 = RAGStore("col_p", tmp_path / "chroma", HashEmbedder())
    assert s2.count() == 1
    assert s2.retrieve("dog content", k=1)[0].text == "dog content"


def test_clear_drops_all(store: RAGStore) -> None:
    store.add(["x", "y"], [{}, {}], ["1", "2"])
    store.clear()
    assert store.count() == 0
