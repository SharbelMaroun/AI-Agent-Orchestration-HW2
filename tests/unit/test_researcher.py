"""Tests for deterministic research assistants."""

from __future__ import annotations

from debate.services.rag.rag_store import Passage
from debate.services.research import build_research_cards
from debate.services.tools.web_search import SearchResult


def test_dogs_research_cards_have_three_specialists() -> None:
    evidence = {
        "search": [
            SearchResult(
                title="AHA dog ownership cardiovascular health",
                url="https://example.org/aha",
                snippet="Dog walking supports heart health.",
            )
        ],
        "rag": [],
    }
    cards = build_research_cards("dogs", evidence)
    assert [card.assistant for card in cards] == [
        "DogsHealthResearcher",
        "DogsUtilityResearcher",
        "DogsBondResearcher",
    ]
    assert cards[0].citation == "https://example.org/aha"
    assert "health" in cards[0].evidence.lower()


def test_cats_research_cards_can_use_rag_metadata_source() -> None:
    evidence = {
        "search": [],
        "rag": [
            Passage(
                text="Bastet and cat poetry show cats as cultural companions.",
                metadata={"source": "cats-cultural-note"},
                distance=0.1,
            )
        ],
    }
    cards = build_research_cards("cats", evidence)
    assert len(cards) == 3
    assert cards[1].assistant == "CatsCultureResearcher"
    assert cards[1].citation == "cats-cultural-note"


def test_research_cards_tolerate_empty_evidence() -> None:
    cards = build_research_cards("dogs", {"search": [], "rag": []})
    assert len(cards) == 3
    assert "No external evidence" in cards[0].evidence
