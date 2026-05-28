"""Embedder — sentence-transformers wrapper. See docs/PRD_rag.md §3.2.

The sentence-transformers model is heavy (~80MB on disk, several seconds to
load). We cache one instance per model name at the class level so multiple
RAGStores in the same process share the model. Loading is lazy: the model
is only fetched the first time `embed_text` or `embed_batch` is called.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    """Lazy-loading wrapper. Override `_load_model` in tests to skip the
    real download — see tests/unit/test_embedder.py."""

    _cache: dict[str, Any] = {}

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """Resolve (and cache) the underlying SentenceTransformer instance.

        HF Hub silence is layered: env vars + warning filters in
        `debate/__init__.py` cover the logger/warnings channels. The
        unauthenticated-requests notice however is written via a direct
        `sys.stderr.write` deep inside `huggingface_hub`, which bypasses
        both the warnings filter chain and the logger level. We suppress
        it with a scoped stderr redirect around the model load only —
        first call per interpreter, ~1s window. Anything emitted during
        normal operation still reaches stderr."""
        cached = type(self)._cache.get(self.model_name)
        if cached is not None:
            return cached
        import contextlib
        import io

        with contextlib.redirect_stderr(io.StringIO()):
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.model_name)
        type(self)._cache[self.model_name] = model
        return model

    @property
    def model(self) -> Any:
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [list(map(float, v)) for v in vectors]

    def dim(self) -> int:
        """Embedding dimensionality (depends on the model)."""
        sample = self.embed_text("dimension probe")
        return len(sample)
