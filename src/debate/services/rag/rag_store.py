"""RAGStore — ChromaDB persistent wrapper, one collection per agent.

See docs/PRD_rag.md §3.1. Per agent we open a separate persistent client at
`data/<agent>/chroma/` and a collection named after the side. The store is
embedder-agnostic — we pass pre-computed vectors so a test fixture can swap
in a deterministic embedder (avoiding the 80MB sentence-transformers
download on CI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel


class EmbedderLike(Protocol):
    def embed_text(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class Passage(BaseModel):
    """One retrieved chunk. `distance` is cosine distance from the query."""

    text: str
    metadata: dict
    distance: float


class RAGStore:
    """ChromaDB-backed retrieval store. Stateless apart from the client/collection."""

    def __init__(
        self,
        collection_name: str,
        persist_dir: str | Path,
        embedder: EmbedderLike,
    ) -> None:
        self.collection_name = collection_name
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        self._client = self._make_client()
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def _make_client(self) -> Any:
        import chromadb

        return chromadb.PersistentClient(path=str(self.persist_dir))

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]) -> int:
        """Insert chunks, skipping any IDs already present. Returns the number
        of *new* chunks inserted so the ingest CLI can log progress."""
        if not documents:
            return 0
        existing = set(self._collection.get(ids=ids).get("ids", []) or [])
        fresh_ids = [i for i in ids if i not in existing]
        if not fresh_ids:
            return 0
        fresh_docs = [d for d, i in zip(documents, ids, strict=True) if i not in existing]
        # Chroma rejects empty metadata dicts; insert a sentinel so callers
        # don't need to know about that quirk.
        fresh_meta = [
            (m or {"_": "_"}) for m, i in zip(metadatas, ids, strict=True) if i not in existing
        ]
        embeddings = self.embedder.embed_batch(fresh_docs)
        self._collection.add(
            documents=fresh_docs,
            metadatas=fresh_meta,
            ids=fresh_ids,
            embeddings=embeddings,
        )
        return len(fresh_ids)

    def retrieve(self, query: str, k: int = 3) -> list[Passage]:
        if not query.strip() or self.count() == 0:
            return []
        vector = self.embedder.embed_text(query)
        result = self._collection.query(
            query_embeddings=[vector],
            n_results=min(k, self.count()),
        )
        passages: list[Passage] = []
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            passages.append(Passage(text=doc, metadata=meta or {}, distance=float(dist)))
        return passages

    def count(self) -> int:
        return int(self._collection.count())

    def clear(self) -> None:
        self._client.delete_collection(name=self.collection_name)
        self._collection = self._client.get_or_create_collection(name=self.collection_name)
