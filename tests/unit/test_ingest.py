"""Unit tests for debate.services.rag.ingest."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from debate.services.rag.ingest import (
    chunk_words,
    ingest_directory,
    parse_frontmatter,
)
from debate.services.rag.rag_store import RAGStore


class HashEmbedder:
    def embed_text(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        return [b / 255.0 for b in hashlib.sha256(text.encode()).digest()[:8]]


_FIXTURE = """---
source: test
type: study
relevance: a, b
---

The quick brown fox jumps over the lazy dog. Repeat. Repeat. Repeat. Done.
"""


def test_parse_frontmatter_extracts_metadata() -> None:
    meta, body = parse_frontmatter(_FIXTURE)
    assert meta["source"] == "test"
    assert meta["type"] == "study"
    assert body.startswith("The quick")


def test_parse_frontmatter_missing_raises() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("no frontmatter here\n")


def test_parse_frontmatter_unclosed_raises() -> None:
    with pytest.raises(ValueError):
        parse_frontmatter("---\nsource: x\nbody starts without closing delim")


def test_chunk_words_respects_size() -> None:
    text = " ".join(str(i) for i in range(10))
    chunks = chunk_words(text, chunk_size=4)
    assert chunks == ["0 1 2 3", "4 5 6 7", "8 9"]


def test_chunk_words_empty() -> None:
    assert chunk_words("", chunk_size=10) == []


def _write_corpus(tmp_path: Path) -> Path:
    (tmp_path / "a.txt").write_text(_FIXTURE, encoding="utf-8")
    (tmp_path / "b.txt").write_text(
        "---\nsource: b\ntype: quote\n---\nShort body here.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_ingest_directory_loads_and_chunks(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_corpus(corpus)
    store = RAGStore("test_col", tmp_path / "chroma", HashEmbedder())
    files, added = ingest_directory(corpus, store, chunk_size=4)
    assert files == 2
    assert added > 0
    assert store.count() == added


def test_ingest_directory_is_idempotent(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_corpus(corpus)
    store = RAGStore("test_col", tmp_path / "chroma", HashEmbedder())
    _, first = ingest_directory(corpus, store, chunk_size=4)
    _, second = ingest_directory(corpus, store, chunk_size=4)
    assert first > 0
    assert second == 0


def test_ingest_directory_empty_corpus(tmp_path: Path) -> None:
    corpus = tmp_path / "empty"
    corpus.mkdir()
    store = RAGStore("test_col", tmp_path / "chroma", HashEmbedder())
    files, added = ingest_directory(corpus, store, chunk_size=10)
    assert (files, added) == (0, 0)
