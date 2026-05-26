"""Deterministic research assistants.

These are tool-like helpers, not extra LLM agents: they convert raw search
and RAG evidence into compact cards the speaking agent can use persuasively.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from debate.shared.schemas import Side


class ResearchCard(BaseModel):
    """One argument-support card passed into a debater prompt."""

    assistant: str
    claim: str
    evidence: str
    judge_angle: str
    citation: str = ""


class ResearchAssistant(BaseModel):
    """A deterministic specialist that selects relevant evidence snippets."""

    name: str
    claim: str
    judge_angle: str
    keywords: tuple[str, ...]

    def build_card(self, evidence: dict[str, list[Any]]) -> ResearchCard:
        hit = _best_evidence(evidence, self.keywords)
        return ResearchCard(
            assistant=self.name,
            claim=self.claim,
            evidence=hit["text"],
            judge_angle=self.judge_angle,
            citation=hit["citation"],
        )


DOGS_ASSISTANTS = (
    ResearchAssistant(
        name="DogsHealthResearcher",
        claim="Dogs win on measurable health and longevity benefits.",
        judge_angle="logos + ethos",
        keywords=("health", "cardio", "mortality", "walking", "therapy", "aha"),
    ),
    ResearchAssistant(
        name="DogsUtilityResearcher",
        claim="Dogs win on service, rescue, protection, and work alongside humans.",
        judge_angle="ethos + clash",
        keywords=("service", "rescue", "police", "military", "working", "hospital"),
    ),
    ResearchAssistant(
        name="DogsBondResearcher",
        claim="Dogs win on active loyalty and reciprocal social bonding.",
        judge_angle="pathos + structure",
        keywords=("loyal", "children", "companion", "cognition", "owner", "bond"),
    ),
)

CATS_ASSISTANTS = (
    ResearchAssistant(
        name="CatsWellbeingResearcher",
        claim="Cats win on calm, low-friction emotional wellbeing.",
        judge_angle="pathos + logos",
        keywords=("stress", "purr", "healing", "allergy", "calm", "wellbeing"),
    ),
    ResearchAssistant(
        name="CatsCultureResearcher",
        claim="Cats win on cultural depth, symbolism, literature, and beauty.",
        judge_angle="ethos + pathos",
        keywords=("bastet", "poetry", "literature", "art", "eliot", "murakami"),
    ),
    ResearchAssistant(
        name="CatsPracticalityResearcher",
        claim="Cats win on independence and suitability for modern homes.",
        judge_angle="logos + clash",
        keywords=("independent", "apartment", "low", "solitude", "urban", "feral"),
    ),
)


def build_research_cards(side: Side, evidence: dict[str, list[Any]]) -> list[ResearchCard]:
    assistants = DOGS_ASSISTANTS if side == "dogs" else CATS_ASSISTANTS
    return [assistant.build_card(evidence) for assistant in assistants]


def _best_evidence(evidence: dict[str, list[Any]], keywords: tuple[str, ...]) -> dict[str, str]:
    candidates = [_coerce_item(item) for item in evidence.get("search", [])]
    candidates.extend(_coerce_item(item) for item in evidence.get("rag", []))
    if not candidates:
        return {
            "text": "No external evidence returned; use persona knowledge carefully.",
            "citation": "",
        }
    for candidate in candidates:
        low = candidate["text"].lower()
        if any(keyword in low for keyword in keywords):
            return candidate
    return candidates[0]


def _coerce_item(item: Any) -> dict[str, str]:
    if isinstance(item, dict):
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("snippet") or item.get("body") or item.get("text") or "").strip()
        citation = str(item.get("url") or item.get("href") or item.get("source") or "").strip()
    else:
        title = str(getattr(item, "title", "")).strip()
        snippet = str(getattr(item, "snippet", "") or getattr(item, "text", "")).strip()
        meta = getattr(item, "metadata", {}) or {}
        citation = str(getattr(item, "url", "") or meta.get("source", "")).strip()
    text = " — ".join(part for part in (title, snippet) if part)
    return {"text": text[:500] if text else str(item)[:500], "citation": citation}
