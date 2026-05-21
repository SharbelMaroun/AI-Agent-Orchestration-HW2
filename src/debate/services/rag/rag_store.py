"""RAGStore — ChromaDB wrapper, one collection per agent. Phase 5.2."""


class Passage:
    """Will become a Pydantic model (text, metadata, distance). Phase 5.2."""


class RAGStore:
    """ChromaDB-backed retrieval store. Phase 5.2."""

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
        """Phase 5.2."""
        raise NotImplementedError

    def retrieve(self, query: str, k: int = 3) -> list[Passage]:
        """Phase 5.2."""
        raise NotImplementedError

    def count(self) -> int:
        """Phase 5.2."""
        raise NotImplementedError
