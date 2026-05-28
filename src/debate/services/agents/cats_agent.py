"""CatsAgent — concrete subclass. side="cats". See docs/PRD_cats.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from debate.services.agents.debate_agent import DebateAgent
from debate.shared.schemas import Ping
from debate.shared.skill_loader import load_agent_skills

DEFAULT_SKILL_PATH = Path("skills/cats")
RAG_COLLECTION = "cats"
LITERARY_KEYWORDS = "literature philosophy culture poetry essay quote"


class CatsAgent(DebateAgent):
    """Pathos + Socratic persona. Search leans toward cultural / literary
    sources so DDG surfaces essays and quotations, not breed-care SEO."""

    side = "cats"

    def __init__(
        self,
        *args: Any,
        system_prompt: str | None = None,
        skill_path: Path | str = DEFAULT_SKILL_PATH,
        **kwargs: Any,
    ) -> None:
        if system_prompt is None:
            system_prompt = load_agent_skills(skill_path)
        kwargs["system_prompt"] = system_prompt
        kwargs.setdefault("agent_id", "cats")
        super().__init__(*args, **kwargs)
        self.rag_collection = RAG_COLLECTION

    def _build_search_query(self, previous_ping: Ping | None) -> str:
        if previous_ping is None:
            return f"cats companion {LITERARY_KEYWORDS}"
        return f"reframe '{previous_ping.text[:80]}' with cat {LITERARY_KEYWORDS}"
