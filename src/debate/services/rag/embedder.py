"""Embedder wrapper around sentence-transformers. Phase 5.1."""


class Embedder:
    """Lazy-loads the sentence-transformers model on first call. Phase 5.1."""

    def embed_text(self, text: str) -> list[float]:
        """Phase 5.1."""
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Phase 5.1."""
        raise NotImplementedError
