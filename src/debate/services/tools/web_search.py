"""Web search tool — DuckDuckGo backend, throttled by ApiGatekeeper.

The agent never calls duckduckgo_search directly; it always goes through
`gatekeeper.execute(WebSearch.search, ...)` so the search service shares the
same rate-limit + retry plumbing as LLM calls (PRD §5 + PRD_gatekeeper.md).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """One hit returned by the search backend."""

    title: str
    url: str
    snippet: str = Field(default="")


class GatekeeperLike(Protocol):
    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any: ...


class DDGBackend:
    """Thin wrapper over duckduckgo_search.DDGS, kept tiny for testability."""

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    def query(self, query: str, max_results: int) -> list[dict]:
        from duckduckgo_search import DDGS

        with DDGS(timeout=self.timeout) as client:
            return list(client.text(query, max_results=max_results))


class WebSearch:
    """Search API. Default backend is DuckDuckGo via `duckduckgo_search`.

    Pass a fake `backend` (any object with `.query(query, max_results) -> list[dict]`)
    in tests to avoid the network entirely.
    """

    def __init__(
        self,
        gatekeeper: GatekeeperLike,
        backend: Any | None = None,
        timeout_seconds: int = 15,
        logger: logging.Logger | None = None,
    ) -> None:
        self.gatekeeper = gatekeeper
        self.backend = backend or DDGBackend(timeout=timeout_seconds)
        self.logger = logger or logging.getLogger("debate.search")

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Run a search query through the gatekeeper. Empty / failed queries
        return an empty list — the agent must tolerate "no evidence today"."""
        if not query.strip():
            return []
        try:
            raw = self.gatekeeper.execute(
                self.backend.query, query, max_results, service="search"
            )
        except Exception as exc:
            self.logger.warning("web search failed query=%r err=%s", query, exc)
            return []
        results: list[SearchResult] = []
        for item in raw or []:
            results.append(
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("href") or item.get("url") or ""),
                    snippet=str(item.get("body") or item.get("snippet") or ""),
                )
            )
        return results
