"""Deterministic research assistants for debate agents."""

from debate.services.research.researcher import (
    ResearchAssistant,
    ResearchCard,
    build_research_cards,
)
from debate.shared.version import __version__

__all__ = ["ResearchAssistant", "ResearchCard", "build_research_cards", "__version__"]
