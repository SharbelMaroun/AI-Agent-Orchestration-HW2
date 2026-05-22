"""Unit tests for debate.services.tools.web_search."""

from __future__ import annotations

from unittest.mock import MagicMock

from debate.services.tools.web_search import SearchResult, WebSearch


class _PassthroughGK:
    """Mimics ApiGatekeeper.execute by just running the call directly."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, api_call, *args, service: str = "default", **kwargs):
        self.calls.append({"service": service, "args": args, "kwargs": kwargs})
        return api_call(*args, **kwargs)


def test_search_returns_results() -> None:
    backend = MagicMock()
    backend.query.return_value = [
        {"title": "Dog longevity study", "href": "http://x/1", "body": "Dogs live 13 years."},
        {"title": "Working dogs", "url": "http://x/2", "snippet": "K9 stats."},
    ]
    gk = _PassthroughGK()
    ws = WebSearch(gatekeeper=gk, backend=backend)
    results = ws.search("dogs longevity", max_results=2)
    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "Dog longevity study"
    assert results[0].url == "http://x/1"
    assert results[0].snippet == "Dogs live 13 years."
    assert results[1].url == "http://x/2"


def test_search_empty_query_short_circuits() -> None:
    backend = MagicMock()
    gk = _PassthroughGK()
    ws = WebSearch(gatekeeper=gk, backend=backend)
    assert ws.search("   ") == []
    backend.query.assert_not_called()
    assert gk.calls == []


def test_search_routes_through_gatekeeper() -> None:
    backend = MagicMock()
    backend.query.return_value = []
    gk = _PassthroughGK()
    WebSearch(gatekeeper=gk, backend=backend).search("hello", max_results=3)
    assert gk.calls[0]["service"] == "search"
    assert gk.calls[0]["args"] == ("hello", 3)


def test_search_swallows_backend_errors() -> None:
    backend = MagicMock()
    backend.query.side_effect = RuntimeError("boom")
    ws = WebSearch(gatekeeper=_PassthroughGK(), backend=backend)
    assert ws.search("anything") == []


def test_search_handles_missing_fields() -> None:
    backend = MagicMock()
    backend.query.return_value = [{"title": "T"}]
    ws = WebSearch(gatekeeper=_PassthroughGK(), backend=backend)
    out = ws.search("q")
    assert out[0].url == ""
    assert out[0].snippet == ""
