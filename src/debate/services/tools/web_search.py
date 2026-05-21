"""Web search tool — DuckDuckGo backend, throttled by gatekeeper. Phase 4.4."""


class SearchResult:
    """Will become a Pydantic model (title, url, snippet). Phase 4.4."""


class WebSearch:
    """HTTP-backed search, routed through ApiGatekeeper. Phase 4.4."""

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Phase 4.4."""
        raise NotImplementedError
