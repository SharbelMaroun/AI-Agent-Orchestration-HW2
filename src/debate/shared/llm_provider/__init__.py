"""Provider-agnostic LLM layer. See docs/PLAN.md ADR-009.

Importing this package triggers each concrete provider module to register
itself in the central registry, so `build_provider("anthropic")` works
without callers needing to know which module defines which provider.
"""

from debate.shared.llm_provider import anthropic_provider, openai_provider  # noqa: F401
from debate.shared.llm_provider.base import (
    LLMProvider,
    build_provider,
    known_providers,
    register,
)

__all__ = ["LLMProvider", "build_provider", "known_providers", "register"]
