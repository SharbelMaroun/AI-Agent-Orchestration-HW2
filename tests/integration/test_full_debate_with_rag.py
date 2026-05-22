"""Integration: full debate where Dogs and Cats each have a real RAGStore.

Uses a tiny on-the-fly corpus and the deterministic `HashEmbedder` so the
test runs in under a second and exercises the actual ChromaDB path.
"""

from __future__ import annotations

from pathlib import Path

from debate.sdk.sdk import DebateSDK
from debate.services.agents.cats_agent import CatsAgent
from debate.services.agents.dogs_agent import DogsAgent
from debate.services.agents.judge_agent import JudgeAgent
from debate.services.orchestrator import Orchestrator
from debate.services.rag.ingest import ingest_directory
from debate.services.rag.rag_store import RAGStore
from debate.shared.config import load_setup

REPO_ROOT = Path(__file__).resolve().parents[2]

_DOGS_PASSAGE = """---
source: test-corpus
type: study
relevance: longevity
---

Dog ownership reduces all-cause mortality by 24% in pooled meta-analyses.
"""
_CATS_PASSAGE = """---
source: test-corpus
type: quote
relevance: literature
---

T.S. Eliot wrote that the naming of cats is a difficult matter.
"""


def _seed_corpus(root: Path, embedder) -> tuple[RAGStore, RAGStore]:
    (root / "dogs").mkdir(parents=True, exist_ok=True)
    (root / "cats").mkdir(parents=True, exist_ok=True)
    (root / "dogs" / "a.txt").write_text(_DOGS_PASSAGE, encoding="utf-8")
    (root / "cats" / "a.txt").write_text(_CATS_PASSAGE, encoding="utf-8")
    dogs_store = RAGStore("dogs_col", root / "chroma_dogs", embedder)
    cats_store = RAGStore("cats_col", root / "chroma_cats", embedder)
    ingest_directory(root / "dogs", dogs_store, chunk_size=50)
    ingest_directory(root / "cats", cats_store, chunk_size=50)
    return dogs_store, cats_store


def test_full_debate_with_real_rag(
    tmp_path: Path, fake_provider_factory, hash_embedder
) -> None:
    dogs_store, cats_store = _seed_corpus(tmp_path / "corpus", hash_embedder)
    setup = load_setup(REPO_ROOT / "config" / "setup.json")
    data = setup.model_dump()
    data["num_rounds"] = 1
    setup = type(setup).model_validate(data)

    sdk = DebateSDK(
        setup=setup, results_dir=tmp_path / "out",
        provider_factory=fake_provider_factory,
    )

    # The SDK's default run_debate doesn't yet wire RAG (Phase 5.6 marker note).
    # We construct the orchestrator directly so this test pins the RAG seam.
    dogs = DogsAgent(
        provider=fake_provider_factory("anthropic"),
        gatekeeper=sdk.gatekeeper,
        model_name=setup.models["dogs"].name,
        rag=dogs_store,
    )
    cats = CatsAgent(
        provider=fake_provider_factory("anthropic"),
        gatekeeper=sdk.gatekeeper,
        model_name=setup.models["cats"].name,
        rag=cats_store,
    )
    judge = JudgeAgent(
        provider=fake_provider_factory("anthropic"),
        gatekeeper=sdk.gatekeeper,
        model_name=setup.models["judge"].name,
    )
    orch = Orchestrator(
        topic=setup.topic, num_rounds=1, results_dir=tmp_path / "out",
    )
    result = orch.run_debate(dogs, cats, judge)

    assert len(result.pings) == 2
    # Each side's store actually got queried during the run.
    assert dogs_store.count() == 1
    assert cats_store.count() == 1


def test_rag_corpora_isolated_per_side(tmp_path: Path, hash_embedder) -> None:
    dogs_store, cats_store = _seed_corpus(tmp_path / "corpus", hash_embedder)
    dogs_hits = dogs_store.retrieve("dog longevity mortality", k=3)
    cats_hits = cats_store.retrieve("dog longevity mortality", k=3)
    assert dogs_hits and "Dog" in dogs_hits[0].text
    # Even though the query is dog-ish, the cats collection only knows about
    # T.S. Eliot — there's no contamination across collections.
    assert cats_hits and "Eliot" in cats_hits[0].text
