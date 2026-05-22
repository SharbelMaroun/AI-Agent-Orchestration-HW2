"""DogsAgent — concrete subclass. side="dogs". See docs/PRD_dogs.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from debate.services.agents.debate_agent import DebateAgent
from debate.shared.schemas import Ping

DEFAULT_PROMPT_PATH = Path("prompts/dogs_system_prompt.md")
RAG_COLLECTION = "dogs"
AUTHORITY_KEYWORDS = "study research longevity cardiovascular working dog AHA"


class DogsAgent(DebateAgent):
    """Logos + ethos persona. Search queries lean toward peer-reviewed and
    authority-laden phrasing so DDG returns studies, not opinion blogs."""

    side = "dogs"

    def __init__(
        self,
        *args: Any,
        system_prompt: str | None = None,
        prompt_path: Path | str = DEFAULT_PROMPT_PATH,
        **kwargs: Any,
    ) -> None:
        if system_prompt is None:
            system_prompt = Path(prompt_path).read_text(encoding="utf-8")
        kwargs["system_prompt"] = system_prompt
        kwargs.setdefault("agent_id", "dogs")
        super().__init__(*args, **kwargs)
        self.rag_collection = RAG_COLLECTION

    def _build_search_query(self, previous_ping: Ping | None) -> str:
        if previous_ping is None:
            return f"dogs better pet {AUTHORITY_KEYWORDS}"
        return f"rebut '{previous_ping.text[:80]}' with dog {AUTHORITY_KEYWORDS}"
