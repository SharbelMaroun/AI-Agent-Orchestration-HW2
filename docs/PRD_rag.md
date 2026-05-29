# PRD — RAG (Retrieval-Augmented Generation)

**Version:** 1.00 · Parent: `docs/PRD.md` · Optional per spec, **included** in this project.
**Status:** Implemented Phase 5. Two implementation notes worth flagging — see end of §3.1 and §3.4.

---

## 1. Purpose
Give the Dogs and Cats agents access to a small, curated **private knowledge base** to enrich arguments beyond what's in the LLM's training data or returned by web search. Each agent has a separate corpus that **reinforces its rhetorical style** (Dogs: studies; Cats: literature).

## 2. Why RAG (rather than dumping the corpus into the system prompt)
- Cheaper: only the top-k relevant chunks reach the LLM per query, not the whole corpus.
- Style-consistent: retrieval finds chunks semantically matched to the current argument.
- Demonstrates the full Agent structure (`LLM + Context + Tools + RAG`) as required by Lesson 05.

## 3. Components

### 3.1 Vector store
- **ChromaDB** in persistent local mode at `data/<agent>/chroma/`.
- One collection per agent: `dogs`, `cats`.
- Judge has **no** RAG (must remain neutral).
- **Implementation note:** ChromaDB rejects empty metadata dicts (`{}`). `RAGStore.add` substitutes `{"_": "_"}` for any missing/empty metadata so callers don't need to know about that quirk. Documented inline in `rag_store.py`.

### 3.2 Embedder
- **`sentence-transformers/all-MiniLM-L6-v2`** — 384-dim, CPU-only, free.
- Loaded once per agent process. Wrapped in `services/rag/embedder.py`.

### 3.3 Corpus
- Manually curated ~15–20 passages per agent.
- Stored as `data/dogs/*.txt` and `data/cats/*.txt`.
- Each file: YAML frontmatter + plain-text body. Frontmatter:
```yaml
---
source: <citation>
type: study | quote | statistic | history
relevance: <comma-separated tags>
---
```

### 3.4 Ingestion (one-time)
- Script: `services/rag/ingest.py`.
- Reads all `.txt` files in the corpus folder, parses frontmatter, chunks by paragraph (max `chunk_size` words from `setup.json`), embeds, stores in ChromaDB with metadata.
- Idempotent: re-running skips already-ingested chunks (keyed by sha1 of `file.name:chunk_index`, truncated to 16 chars).
- Run as: `uv run python -m debate.services.rag.ingest --agent dogs` (or via `just ingest-dogs` / `just ingest-cats` / `just ingest`).
- **Implementation note:** YAML frontmatter is parsed by a small `key: value` line parser rather than PyYAML — keeps the dependency footprint smaller and surfaces frontmatter authoring mistakes immediately. The shape is the same as PyYAML would accept for flat key/value documents.

### 3.5 Retrieval
- API: `RAGStore.retrieve(query: str, k: int = 3) -> list[Passage]`.
- Returns top-k semantically similar chunks with metadata.
- Called by Pro/Con agent inside their per-round logic, **before** producing the ping.

## 4. Integration with the Agent Loop
```
For each round (Dogs or Cats):
  1. Read opponent's last ping
  2. Decide a search query (LLM call OR heuristic)
  3. results = web_search.search(query)
  4. passages = rag_store.retrieve(query, k=3)
  5. ping = llm.generate(system_prompt, history, results, passages)
  6. emit ping (with citations referring to BOTH web URLs and RAG sources)
```

## 5. Configuration (`config/setup.json.rag`)
```json
{
  "k": 3,
  "chunk_size": 300,
  "embedder": "sentence-transformers/all-MiniLM-L6-v2",
  "persist_dir": "data/{agent}/chroma"
}
```

## 6. Acceptance Criteria
- Each agent's corpus has ≥ 15 passages, each ≤ 300 words.
- `ingest.py` succeeds on a fresh repo and is idempotent on second run.
- `retrieve("loyalty studies", k=3)` for the Dogs corpus returns 3 relevant chunks.
- `retrieve("cat independence philosophy", k=3)` for the Cats corpus returns 3 relevant chunks.
- Every Dogs/Cats ping during a full debate includes ≥ 1 RAG citation in its `citations` field.

## 7. Test Scenarios
- **Ingest from scratch:** delete chroma dir → run ingest → ≥ 15 chunks indexed.
- **Re-ingest:** run ingest twice → second run is a no-op.
- **Retrieval relevance:** for a known query, top-1 chunk matches a known-relevant file (manual fixture).
- **Empty corpus:** delete all .txt files → `retrieve()` returns `[]` without crashing.
- **Cross-contamination:** ensure Dogs queries never return Cats chunks (separate collections).

## 8. Out of scope
- Reranking with a cross-encoder.
- Updating the corpus from web search results (corpus is static post-ingest).
- Multi-modal RAG (text only).

## 9. Alternatives considered
| Option | Chosen? | Rationale |
|---|---|---|
| **ChromaDB** (embedded, persistent) vs FAISS / pgvector / in-memory | ✅ Chroma | Zero-setup, file-backed persistence under `data/<agent>/chroma/`, per-collection isolation — no server to run on a fresh clone. FAISS needs a separate id→text map; pgvector needs a DB. |
| **`all-MiniLM-L6-v2`** (384-dim, CPU) vs `all-mpnet-base-v2` / remote embedding API | ✅ MiniLM | Free, local, fast on CPU, no key, no rate limit; quality is ample for 15-passage corpora. A remote API would re-introduce the cost/latency RAG was meant to avoid. |
| **Hand-rolled `key: value` frontmatter parser** vs PyYAML | ✅ hand parser | Smaller dependency footprint; surfaces authoring typos immediately; the corpus only needs flat key/value frontmatter. |
| **Word-count chunking** vs sentence/semantic chunking | ✅ word chunks | Deterministic, dependency-free, adequate for short curated passages; semantic chunking adds a model for no measurable retrieval gain here. |
| Cross-encoder reranking | ❌ (out of scope) | Marginal gain over bi-encoder top-k for a tiny corpus; adds a second model + latency. |

## 10. Performance metrics
- **Embedding:** 384-dim vectors; model loaded **once per process** (class-level cache in `embedder.py`), CPU-only, no GPU.
- **Corpus:** ≥ 15 passages/side, ≤ 300 words each; two disjoint collections.
- **Retrieval:** top-`k=3` per query; one `retrieve()` per speaking ping (≈ 10/side/debate).
- **Ingestion:** idempotent — re-runs skip already-stored chunks via a sha1(`file:idx`) key truncated to 16 chars; first-run indexes the whole corpus in a single pass.
