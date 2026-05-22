"""Corpus ingestion: data/<agent>/*.txt → ChromaDB. See docs/PRD_rag.md §3.4.

Each .txt file has YAML-ish frontmatter (between `---` markers) and a body.
We avoid the PyYAML dependency by parsing the simple `key: value` shape
ourselves — anything more complex would mask an authoring mistake.

Usage:
    uv run python -m debate.services.rag.ingest --agent dogs
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from debate.shared.config import load_setup

from .embedder import Embedder
from .rag_store import RAGStore

FRONTMATTER_DELIM = "---"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Raises ValueError if frontmatter missing."""
    stripped = text.lstrip()
    if not stripped.startswith(FRONTMATTER_DELIM):
        raise ValueError("missing YAML frontmatter")
    parts = stripped.split(FRONTMATTER_DELIM, 2)
    if len(parts) < 3:
        raise ValueError("frontmatter not closed with '---'")
    meta_block, body = parts[1], parts[2]
    meta: dict = {}
    for line in meta_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.strip()


def chunk_words(text: str, chunk_size: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [
        " ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)
    ]


def _chunk_id(file_path: Path, index: int) -> str:
    raw = f"{file_path.name}:{index}".encode()
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:16]


def ingest_directory(
    corpus_dir: Path, store: RAGStore, chunk_size: int
) -> tuple[int, int]:
    """Walk `corpus_dir/*.txt`, chunk, and add to `store`. Returns
    (files_seen, chunks_added). Idempotent — re-running adds zero chunks."""
    files = sorted(corpus_dir.glob("*.txt"))
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        for i, chunk in enumerate(chunk_words(body, chunk_size)):
            documents.append(chunk)
            metadatas.append({**meta, "file": f.name, "chunk_index": i})
            ids.append(_chunk_id(f, i))
    added = store.add(documents, metadatas, ids)
    return len(files), added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a RAG corpus.")
    parser.add_argument("--agent", required=True, choices=["dogs", "cats"])
    parser.add_argument("--config", default="config/setup.json")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args(argv)

    cfg = load_setup(args.config)
    corpus = Path(args.data_root) / args.agent
    persist = Path(cfg.rag.persist_dir.replace("{agent}", args.agent))
    store = RAGStore(
        collection_name=args.agent,
        persist_dir=persist,
        embedder=Embedder(cfg.rag.embedder),
    )
    files, added = ingest_directory(corpus, store, cfg.rag.chunk_size)
    print(f"ingest agent={args.agent} files={files} chunks_added={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
