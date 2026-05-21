"""Pydantic JSON message schemas. See docs/PLAN.md §6 for full spec.

Implementation pending Phase 3.1. Stubs ensure the names are importable.
"""


class ChatMessage:
    """Will become Pydantic BaseModel (role, content). Phase 3.1."""


class CompletionResponse:
    """Returned by LLMProvider.complete. Phase 3.1."""


class Ping:
    """One debate turn. Phase 3.1."""


class Score:
    """Judge's per-ping score. Phase 3.1."""


class Verdict:
    """Final outcome with winner + rationale + key points. Phase 3.1."""


class DebateResult:
    """Wraps full debate output for persistence. Phase 3.1."""


class OpeningBrief:
    """Setup envelope sent to all agents. Phase 3.1."""


class YourTurn:
    """Signal-to-act envelope. Phase 3.1."""
