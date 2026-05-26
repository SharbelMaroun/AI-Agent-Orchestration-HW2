"""Runtime wiring helpers shared by SDK and process workers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from debate.services.rag.embedder import Embedder
from debate.services.rag.rag_store import RAGStore
from debate.services.tools.web_search import WebSearch
from debate.shared.config import SetupConfig


def build_search_tool(setup: SetupConfig, gatekeeper: Any) -> WebSearch | None:
    if setup.search.provider != "duckduckgo":
        return None
    return WebSearch(
        gatekeeper=gatekeeper,
        timeout_seconds=setup.search.timeout_seconds,
    )


def build_rag_store(side: str, setup: SetupConfig) -> RAGStore | None:
    if not setup.rag.enabled:
        return None
    persist_dir = Path(setup.rag.persist_dir.replace("{agent}", side))
    return RAGStore(
        collection_name=side,
        persist_dir=persist_dir,
        embedder=Embedder(setup.rag.embedder),
    )


def speaking_agent_kwargs(side: str, setup: SetupConfig, gatekeeper: Any) -> dict:
    return {
        "rag": build_rag_store(side, setup),
        "search_tool": build_search_tool(setup, gatekeeper),
        "rag_k": setup.rag.k,
        "search_max_results": setup.search.max_results,
    }
