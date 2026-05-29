"""Pure-function helpers used by `DebateAgent` — JSON parsing of LLM
replies, clash validation, user-prompt assembly. Extracted so
`debate_agent.py` stays under the raw line cap."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from debate.services.agents._json_block import JSON_BLOCK_RE
from debate.shared.schemas import Ping, Side
from debate.shared.security import SecuritySanitizer


def sanitize_search_hit(hit, sanitizer: SecuritySanitizer):
    for field in ("title", "snippet"):
        if hasattr(hit, field):
            setattr(hit, field, sanitizer.sanitize_external(getattr(hit, field) or ""))
    return hit


def sanitize_rag_passage(passage, sanitizer: SecuritySanitizer):
    if hasattr(passage, "text"):
        passage.text = sanitizer.sanitize_external(passage.text or "")
    return passage


def sanitize_hits(hits, sanitizer: SecuritySanitizer):
    return [sanitize_search_hit(h, sanitizer) for h in hits]


def sanitize_passages(passages, sanitizer: SecuritySanitizer):
    return [sanitize_rag_passage(p, sanitizer) for p in passages]


class ClashViolationError(ValueError):
    """Ping past round 1 must clash with the opponent's previous ping."""


class PingParseError(ValueError):
    """Raised when the LLM's reply cannot be parsed into a Ping."""


def parse_ping_json(text: str, *, side: Side, round_: int) -> Ping:
    """Extract the first JSON object from the LLM reply and validate it.
    Tolerates prose around the JSON block so a polite preface doesn't crash."""
    match = JSON_BLOCK_RE.search(text)
    if not match:
        raise PingParseError("no JSON object found in LLM reply")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise PingParseError(f"invalid JSON in reply: {exc}") from exc
    payload.setdefault("round", round_)
    payload.setdefault("side", side)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    try:
        return Ping.model_validate(payload)
    except Exception as exc:  # pydantic ValidationError, re-wrapped
        raise PingParseError(f"reply did not match Ping schema: {exc}") from exc


def validate_clash(ping: Ping, previous_ping: Ping | None) -> None:
    """Round 1 has no opponent ping to clash with. From round 2 onward,
    the new ping must reference the prior round's ping by its round number."""
    if previous_ping is None:
        return
    if ping.refers_to_ping != previous_ping.round:
        raise ClashViolationError(
            f"ping for round {ping.round} must refer to opponent ping "
            f"{previous_ping.round}, got refers_to_ping={ping.refers_to_ping}"
        )


def build_user_prompt(
    side: Side,
    previous_ping: Ping | None,
    evidence: dict,
    round_: int,
) -> str:
    prior = (
        ""
        if previous_ping is None
        else (
            f"\nOpponent's previous ping (round {previous_ping.round}, "
            f"side {previous_ping.side}):\n{previous_ping.text}\n"
        )
    )
    return (
        f"Round {round_}. You are arguing for the side: {side}.\n"
        f"{prior}\n"
        f"Research assistant cards: {evidence.get('research_cards', [])}\n"
        f"Web search evidence: {evidence['search']}\n"
        f"RAG passages: {evidence['rag']}\n\n"
        "Prefer the strongest research cards for the Judge's rubric. "
        "Respond with ONE JSON object matching the Ping schema. "
        "If this is round 2+, set `refers_to_ping` to the opponent's round."
    )
