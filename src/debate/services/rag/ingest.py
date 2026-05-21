"""Corpus ingestion CLI. Reads data/<agent>/*.txt → ChromaDB. Phase 5.3.

Usage (after implementation):
    uv run python -m debate.services.rag.ingest --agent dogs
    uv run python -m debate.services.rag.ingest --agent cats
"""


def main() -> None:
    """Parse CLI, load corpus, chunk, embed, insert into RAGStore. Phase 5.3."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
