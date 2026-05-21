# Architecture & Design Plan (PLAN)

**Version:** 1.00 · **Status:** Draft · References: `docs/PRD.md`

---

## 1. C4 Model — Context

```
+--------------------------------------------------------+
|                   External Actors                       |
|  - Examiner (runs the CLI)                              |
|  - Anthropic API (LLM)                                  |
|  - Web Search Provider (e.g., DuckDuckGo / Tavily)      |
|  - Embedding Model (sentence-transformers, local)       |
+----------------------------|----------------------------+
                             v
+--------------------------------------------------------+
|              AI Agent Debate System                     |
|   - 3 agents (Pro-Dogs, Pro-Cats, Judge)                |
|   - Orchestrator, Gatekeeper, Watchdog, RAG, Logger     |
|   - Terminal CLI menu                                   |
+--------------------------------------------------------+
```

## 2. C4 Model — Container

```
[ User Terminal (CLI Menu) ]
            |
            v
[      debate.sdk.DebateSDK      ]  <-- single entry point
            |
   +--------+--------+-------------------+
   v                 v                   v
[ Orchestrator ]  [ Gatekeeper ]   [ Watchdog ]
   |                 |                   |
   +----+----+----+--+-------------------+
   |    |    |    |
   v    v    v    v
 [Pro] [Con][Judge][Logger]
   |    |
   |    +---> RAG (chromadb)
   +--------> RAG (chromadb)
   |
   +--------> Web Search
   |
   +--------> Anthropic API   (all via Gatekeeper)
```

## 3. C4 Model — Component (Python package layout)

```
src/debate/
├── __init__.py                  # exports __version__, public SDK
├── main.py                      # entry point: CLI menu
│
├── sdk/
│   ├── __init__.py
│   └── sdk.py                   # DebateSDK — public API for all consumers
│
├── services/
│   ├── __init__.py
│   ├── orchestrator.py          # Drives the debate loop
│   ├── watchdog.py              # Keep-alive + restart
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py        # Abstract BaseAgent
│   │   ├── dogs_agent.py        # logos/ethos persona
│   │   ├── cats_agent.py        # pathos/Socratic persona
│   │   └── judge_agent.py       # 5-dim rubric judge
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── rag_store.py         # ChromaDB wrapper
│   │   ├── embedder.py          # sentence-transformers wrapper
│   │   └── ingest.py            # one-time corpus loader
│   │
│   └── tools/
│       ├── __init__.py
│       └── web_search.py        # HTTP wrapper for search provider
│
└── shared/
    ├── __init__.py
    ├── gatekeeper.py            # ApiGatekeeper class
    ├── config.py                # Config loader + version validator
    ├── version.py               # __version__ = "1.00"
    ├── constants.py             # Enum + literal constants only
    ├── logger.py                # FIFO-rotating logger
    ├── schemas.py               # Pydantic JSON message schemas
    └── llm_provider/            # Provider-agnostic LLM layer
        ├── __init__.py          # exports LLMProvider, build_provider()
        ├── base.py              # LLMProvider ABC + CompletionResponse
        ├── anthropic_provider.py
        └── openai_provider.py
```

## 4. Class Diagram (text)

```
                       BaseAgent (abstract)
                       - id: str
                       - system_prompt: str
                       - provider: LLMProvider
                       - gatekeeper: ApiGatekeeper
                       - history: list[ChatMessage]
                       - logger: Logger
                       + generate(prompt, context) -> Message
                       + receive(message) -> None
                              ^
                              |
       +----------------------+----------------------+
       |                                             |
  DebateAgent (abstract)                       JudgeAgent
  - rag: RAGStore                              - rubric: Rubric
  - search_tool: WebSearch                     - scores: dict
  + use_rag(query) -> list[str]                + score_ping(ping) -> Score
  + search(query) -> list[Result]              + decide_winner() -> Verdict
              ^
              |
    +---------+---------+
    |                   |
 DogsAgent          CatsAgent
 (logos/ethos)      (pathos/Socratic)


LLMProvider (abstract)
+ complete(system, messages, model, max_tokens) -> CompletionResponse
    ^
    |
+---+---+---------+
|       |         |
Anthropic OpenAI  Google
Provider  Provider Provider



ApiGatekeeper
- rate_config: RateLimitConfig
- token_log: list[TokenUsage]
- queue: FIFOQueue
+ execute(api_call, *args, **kwargs) -> Response
+ get_queue_status() -> QueueStatus
+ get_token_summary() -> CostReport


Watchdog
- agents: list[BaseAgent]
- heartbeat_interval: float
- timeout: float
+ start() / stop()
+ on_heartbeat(agent_id) -> None
+ on_timeout(agent_id) -> None       # kill + restart


Orchestrator
- judge: JudgeAgent
- pro: ProDogsAgent
- con: ConCatsAgent
- num_rounds: int
- watchdog: Watchdog
+ run_debate() -> DebateResult


RAGStore
- collection: chromadb.Collection
- embedder: Embedder
+ add(documents: list[str]) -> None
+ retrieve(query: str, k: int) -> list[str]


DebateSDK  (sole public entry)
+ run_debate(topic: str = "cats vs dogs") -> DebateResult
+ get_last_verdict() -> Verdict
+ get_cost_report() -> CostReport
```

## 5. Architectural Decision Records (ADRs)

### ADR-001: Process model — multiprocessing vs subprocess
**Decision:** Use Python `multiprocessing.Process` per agent, with `multiprocessing.Queue` for IPC.
**Rationale:** Satisfies the lecture's "agent = process" rule, keeps everything in one Python project (no need to launch Claude CLI from Python), simpler debugging, OS-agnostic. JSON messages flow through queues.
**Alternatives considered:** `subprocess` spawning `claude` CLI per agent — more authentic to the lecture's mental model but harder to test, harder to capture costs, fragile on Windows.
**Trade-off:** We use the Anthropic Python SDK directly inside each child process instead of running Claude CLI. The conceptual structure (3 processes + IPC) is preserved.

### ADR-002: LLM provider — default Anthropic, abstraction allows any
**Decision:** Default to Anthropic Claude via the `anthropic` Python SDK, but route every call through the `LLMProvider` abstraction (ADR-009). Provider per agent is configurable in `config/setup.json.models.<side>.provider`.
**Rationale:** Anthropic's SDK has clean token-usage reporting (`response.usage.*`) and native prompt caching support. But we don't lock in — the same code works with OpenAI, Google, or any future provider once a `LLMProvider` subclass is added.
**Default models:** `claude-haiku-4-5-20251001` for Dogs and Cats (cheap, fast, sufficient for rhetoric) and `claude-sonnet-4-6` for Judge (more careful evaluation). Both configurable.

### ADR-003: Vector store — ChromaDB
**Decision:** ChromaDB, local persistent mode.
**Rationale:** Zero-setup, embedded, local file storage, free. Sufficient for ≤ 1000 chunks per corpus.
**Alternatives:** Pinecone (cloud, costs money, overkill), FAISS (no metadata, manual), pgvector (requires Postgres).

### ADR-004: Embedding model — sentence-transformers/all-MiniLM-L6-v2
**Decision:** Local `sentence-transformers` model.
**Rationale:** Free, fast, runs CPU-only, 384-dim vectors. No API calls during retrieval → not gated by Gatekeeper (only API calls are).
**Trade-off:** Slightly lower quality than provider embedding APIs (OpenAI text-embedding-3-small), but the gap is tiny for our small corpus and price is the deciding factor.

### ADR-005: IPC format — JSON via Pydantic schemas
**Decision:** Every message between processes is a JSON-serialized Pydantic model.
**Rationale:** Lecture explicitly requires JSON. Pydantic gives free schema validation and IDE autocomplete. Token-efficient and monitorable.

### ADR-006: Logging — Python `logging` + custom FIFO `RotatingFileHandler`
**Decision:** Wrap stdlib `logging.handlers.RotatingFileHandler` with a custom subclass that enforces N files × M lines from `config/logging_config.json`.
**Rationale:** Matches the lecture's "20 files × 500 lines" example, leverages stdlib.

### ADR-007: Web search provider — DuckDuckGo via `duckduckgo-search`
**Decision:** Use `duckduckgo-search` Python package — free, no API key needed.
**Rationale:** Avoids extra paid API setup. Throttled by Gatekeeper.
**Fallback:** Tavily free tier if DDG becomes unreliable.

### ADR-009: LLM provider abstraction (`LLMProvider`)
**Decision:** Introduce a thin `LLMProvider` ABC with one method, `complete(system, messages, model, max_tokens) -> CompletionResponse`. Provide concrete `AnthropicProvider` and `OpenAIProvider` (Google later if needed). Each agent holds a `provider: LLMProvider` instance built via `build_provider(provider_name)` from config. The Gatekeeper wraps `provider.complete` — the abstraction does **not** replace the Gatekeeper, it sits inside it.
**Rationale:** Avoids vendor lock-in without pulling in heavy frameworks like LangChain. ~50 LOC per provider. Lets the lecturer / partner swap providers via JSON without touching Python. Keeps all token + cost tracking centralized in the Gatekeeper (the abstraction returns a uniform `CompletionResponse` with normalized `input_tokens` / `output_tokens` / cache fields).
**Trade-off vs. LiteLLM:** LiteLLM is a single dependency that maps ~100 providers — but its abstractions can leak when providers diverge (cache headers, streaming, tool schemas). Hand-rolled wrappers are explicit, auditable, and zero new transitive deps. Upgrade path remains open.
**Trade-off vs. LangChain:** LangChain wants to own the LLM call (and the whole chain), which conflicts with the Gatekeeper. Out.

### ADR-008: Agent memory — per-agent history with Anthropic prompt caching
**Decision:** Each agent process maintains its own `history: list[Message]` in memory. On every round, the agent appends the incoming `YOUR_TURN` (with the opponent's last ping) to its history, calls `anthropic_client.messages.create(messages=history, ...)`, then appends the assistant response. Enable Anthropic prompt caching on the system prompt and the early conversation prefix.
**Rationale:** The Anthropic API is stateless — every call must include the full conversation. By keeping the history local to each agent process, we minimize coordination overhead and preserve isolation (each agent only sees what the protocol sends it). Prompt caching reduces input cost of re-sent history by ~90% on the cached portion.
**Trade-off:** Memory grows linearly with rounds. At 10 rounds × 250 words × 2 sides ≈ 7.5K tokens per call by the final round — small enough to be acceptable. Cache hits keep effective spend modest. Histories are reset between debates (no persistence required).

## 6. Data Schemas (Pydantic, lives in `shared/schemas.py`)

```python
Side = Literal["dogs", "cats"]

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class CompletionResponse(BaseModel):     # returned by LLMProvider.complete
    text: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    model: str
    provider: str

class Ping(BaseModel):
    round: int
    side: Side
    text: str
    citations: list[str]              # URLs / RAG chunks referenced
    refers_to_ping: int | None        # which previous ping this clashes with
    timestamp: datetime
    tokens_in: int
    tokens_out: int

class Score(BaseModel):
    ping_round: int
    side: Side
    structure: int       # 0-3
    logos: int
    pathos: int
    ethos: int
    clash: int
    rationale: str       # 1-2 sentence judge note

class Verdict(BaseModel):
    winner: Side
    dogs_total: int
    cats_total: int
    margin: int
    written_rationale: str
    key_points_dogs: list[str]
    key_points_cats: list[str]

class DebateResult(BaseModel):
    topic: str
    pings: list[Ping]
    scores: list[Score]
    verdict: Verdict
    cost_report: dict
    started_at: datetime
    finished_at: datetime
```

## 7. Configuration Files

### `config/setup.json`
```json
{
  "version": "1.00",
  "topic": "Are cats or dogs the better pet?",
  "num_rounds": 10,
  "models": {
    "dogs":  { "provider": "anthropic", "name": "claude-haiku-4-5-20251001" },
    "cats":  { "provider": "anthropic", "name": "claude-haiku-4-5-20251001" },
    "judge": { "provider": "anthropic", "name": "claude-sonnet-4-6" }
  },
  "timeouts": {
    "agent_response_seconds": 60,
    "watchdog_heartbeat_seconds": 5,
    "watchdog_kill_after_seconds": 90
  },
  "rag": {
    "k": 3,
    "chunk_size": 300,
    "embedder": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "budget_usd": 5.00
}
```

### `.env.example`
Documents every environment variable the project may read. The actual `.env` is gitignored.
```bash
# REQUIRED for the default config (Anthropic for all three agents).
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# OPTIONAL — needed only if you switch an agent's provider in config/setup.json.
# OPENAI_API_KEY=your-openai-api-key-here
# GOOGLE_API_KEY=your-google-api-key-here

# OPTIONAL — web search fallback. DuckDuckGo is default and needs no key.
# TAVILY_API_KEY=your-tavily-key-if-using-tavily
```

### `config/rate_limits.json`
```json
{
  "version": "1.00",
  "services": {
    "default": {
      "requests_per_minute": 30,
      "requests_per_hour": 500,
      "concurrent_max": 5,
      "retry_after_seconds": 30,
      "max_retries": 3
    },
    "search": {
      "requests_per_minute": 20,
      "concurrent_max": 2
    }
  }
}
```

### `config/logging_config.json`
```json
{
  "version": "1.00",
  "level": "INFO",
  "max_files": 20,
  "max_lines_per_file": 500,
  "directory": "results/logs/"
}
```

## 8. Deployment / Runtime Topology

Single-machine: parent Python process forks 3 children (Pro, Con, Judge). Each child holds:
- A `BaseAgent` instance with its system prompt
- A reference to the shared `ApiGatekeeper` (via manager proxy)
- Its own `RAGStore` (Pro/Con only)

The Judge is the parent's direct child but does **not** spawn Pro/Con — the Orchestrator (in the main process) spawns all three.

## 9. Open Questions
1. **Which web search package** — `duckduckgo-search` vs `tavily-python` (free tier)? Decision deferred to Phase 2 spike.
2. **RAG corpus assembly** — manual curation (15–20 hand-picked passages per side) vs. automated scraping. Recommend manual for Stage 4 to control quality.
3. **Pair partner's role** — who codes which module? Resolve before Phase 2.
