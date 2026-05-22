# TODO — AI Agent Orchestration HW2

**Version:** 1.00 · References `docs/PRD.md`, `docs/PLAN.md`

**Status legend:** ⬜ Not Started · 🟨 In Progress · ✅ Completed
**Owner key:** S = Sharbel · P = Partner · ☆ = either
**DoD per task:** the deliverable is on disk, syntactically valid, passes its smoke-check (compiles / lints / type-checks / referenced test passes if applicable).

Total tasks target: 500–700 atomic. Phases are roughly sequential but tasks within a phase may be parallelized across the pair.

---

## Phase 0 — Documentation & Design (currently 🟨)

### 0.1 Repository scaffolding
- [x] Create `CLAUDE.md` with project guidelines
- [x] Create `.gitignore` with secrets + Python + Claude excludes
- [x] Create `.env.example` template
- [x] Initialize git repo and link to GitHub remote
- [x] First commit pushed to `main`
- [ ] Add repo description + topics on GitHub web UI
- [ ] Confirm repo visibility (public per submission rules)
- [ ] Share repo with partner (collaborator access)

### 0.2 Main PRD (`docs/PRD.md`)
- [x] Draft §1 Overview + topic justification
- [x] Draft §2 Goals + 10 functional KPIs + 6 non-functional KPIs
- [x] Draft §3 Functional requirements (architecture, debate loop, sync invariant, memory model, rubric, personas, tools, comms)
- [x] Draft §4 Non-functional requirements
- [x] Draft §5 Assumptions, dependencies, constraints, env vars, out-of-scope
- [x] Draft §6 Phases + timeline
- [x] Draft §7 Final acceptance test checklist
- [x] Draft §8 References
- [ ] Partner review of PRD §1–4
- [ ] Partner review of PRD §5–8
- [ ] Resolve PRD review comments

### 0.3 Architecture plan (`docs/PLAN.md`)
- [x] Draft C4 Context + Container + Component diagrams (text)
- [x] Draft full Python package layout tree
- [x] Draft class hierarchy text diagram
- [x] Draft ADR-001 to ADR-009
- [x] Draft Pydantic schemas section
- [x] Draft config file shapes (setup.json, rate_limits.json, logging_config.json, .env.example)
- [x] Open Questions section
- [ ] Partner review of PLAN
- [ ] Resolve PLAN review comments

### 0.4 Per-mechanism PRDs
- [x] `PRD_judge.md` — rubric, system prompt, anti-collusion, tie-breakers
- [x] `PRD_dogs.md` — persona, RAG corpus design, system prompt
- [x] `PRD_cats.md` — persona, RAG corpus design, system prompt
- [x] `PRD_gatekeeper.md` — rate limits, retries, queue, cost tracking, caching
- [x] `PRD_rag.md` — chroma, embedder, ingest, retrieve
- [x] `PRD_watchdog.md` — heartbeat, restart, fatal handling
- [x] `PROMPTS.md` template + initial 2 entries
- [ ] Partner review of all per-mechanism PRDs
- [ ] Resolve per-mechanism PRD review comments

### 0.5 This TODO
- [x] Phase 0 task list
- [x] Phase 1 task list
- [x] Phase 2 task list
- [x] Phase 3 task list
- [x] Phase 4 task list
- [x] Phase 5 task list
- [x] Phase 6 task list
- [x] Phase 7 task list
- [x] Phase 8 task list
- [ ] Partner reviews TODO + assigns owners (S/P/☆) per task
- [ ] Commit TODO with owner column filled in

---

## Phase 1 — Manual Debate (Stage 1 deliverable for README)

### 1.1 Setup
- [ ] Install Claude CLI locally (if not already)
- [ ] Verify `claude --version` runs on Sharbel's machine
- [ ] Verify Claude CLI runs on partner's machine
- [ ] Choose final debate topic phrasing for Stage 1: "Are dogs or cats the better pet?"
- [ ] Write the manual judge instructions (one paragraph)
- [ ] Write the manual Dogs-agent role instructions
- [ ] Write the manual Cats-agent role instructions
- [ ] Decide manual ping word limit (e.g., 150 words for speed)
- [ ] Open two Claude CLI windows side by side

### 1.2 Run the manual debate
- [ ] Brief Dogs CLI session with role + topic + rules
- [ ] Brief Cats CLI session with role + topic + rules
- [ ] Round 1 — Dogs opens (ping copied into transcript)
- [ ] Round 1 — Cats responds (paste Dogs ping into Cats CLI)
- [ ] Round 2 — Dogs counters (paste Cats ping into Dogs CLI)
- [ ] Round 2 — Cats counters
- [ ] Round 3 — Dogs
- [ ] Round 3 — Cats
- [ ] Round 4 — Dogs
- [ ] Round 4 — Cats
- [ ] Round 5 — Dogs
- [ ] Round 5 — Cats
- [ ] Round 6 — Dogs
- [ ] Round 6 — Cats
- [ ] Round 7 — Dogs
- [ ] Round 7 — Cats
- [ ] Round 8 — Dogs
- [ ] Round 8 — Cats
- [ ] Round 9 — Dogs
- [ ] Round 9 — Cats
- [ ] Round 10 — Dogs
- [ ] Round 10 — Cats
- [ ] You (human) judge it: pick a winner + write 3-sentence rationale

### 1.3 Capture artifacts
- [ ] Save full transcript to `results/manual_stage1/transcript.md`
- [ ] Save human-judge verdict to `results/manual_stage1/verdict.md`
- [ ] Take screenshot of the two CLI windows mid-debate
- [ ] Save screenshot to `assets/manual_stage1/two_cli_windows.png`
- [ ] Write 1-paragraph reflection: "what we learned from the manual run"
- [ ] Add reflection to `docs/PROMPTS.md`

---

## Phase 2 — Project Bootstrap

### 2.1 `pyproject.toml`
- [x] Create `pyproject.toml` with `[project]` metadata (name, version, authors, description)
- [x] Add `[project] requires-python = ">=3.10"`
- [x] Add core deps: anthropic, pydantic, python-dotenv
- [x] Add provider dep (optional): openai
- [x] Add data deps: chromadb, sentence-transformers
- [x] Add tool deps: duckduckgo-search
- [x] Add dev deps: pytest, pytest-cov, ruff
- [x] Add `[tool.ruff]` config: line-length=100, target-version=py310
- [x] Add `[tool.ruff.lint]` select + ignore (per CLAUDE.md §7)
- [x] Add `[tool.coverage.run]` source/omit (per CLAUDE.md §6)
- [x] Add `[tool.coverage.report] fail_under = 85`
- [x] Add `[tool.pytest.ini_options]` minimal config
- [x] Add `[project.scripts] debate = "debate.main:cli"`
- [x] Run `uv sync` and verify success
- [x] Verify `uv.lock` was generated
- [x] Commit `uv.lock`
- [x] Create `LICENSE` (MIT, 2026, Sharbel Maroun + Amr Safadi)
- [x] Create placeholder `README.md` (stub for build-backend; full content in Phase 7.2)

### 2.2 Config files
- [x] Create `config/setup.json` with shape from PLAN.md §7
- [x] Verify `setup.json` parses as valid JSON
- [x] Create `config/rate_limits.json` with shape from PLAN.md §7
- [x] Verify `rate_limits.json` parses
- [x] Create `config/logging_config.json` with shape from PLAN.md §7
- [x] Verify `logging_config.json` parses
- [x] Add `version` key (= "1.00") to all three configs

### 2.3 Package skeleton (`src/debate/`)
- [x] Create `src/debate/__init__.py` with `__version__ = "1.00"`
- [x] Add `__all__` in `__init__.py` (initially empty list)
- [x] Create `src/debate/main.py` with a placeholder `cli()` entrypoint
- [x] Create `src/debate/sdk/__init__.py`
- [x] Create `src/debate/sdk/sdk.py` with empty `DebateSDK` class skeleton
- [x] Create `src/debate/services/__init__.py`
- [x] Create `src/debate/services/orchestrator.py` with empty class skeleton
- [x] Create `src/debate/services/watchdog.py` with empty class skeleton
- [x] Create `src/debate/services/agents/__init__.py`
- [x] Create `src/debate/services/agents/base_agent.py` with abstract class skeleton
- [x] Create `src/debate/services/agents/dogs_agent.py` with class skeleton
- [x] Create `src/debate/services/agents/cats_agent.py` with class skeleton
- [x] Create `src/debate/services/agents/judge_agent.py` with class skeleton
- [x] Create `src/debate/services/rag/__init__.py`
- [x] Create `src/debate/services/rag/embedder.py` skeleton
- [x] Create `src/debate/services/rag/rag_store.py` skeleton
- [x] Create `src/debate/services/rag/ingest.py` skeleton
- [x] Create `src/debate/services/tools/__init__.py`
- [x] Create `src/debate/services/tools/web_search.py` skeleton
- [x] Create `src/debate/shared/__init__.py`
- [x] Create `src/debate/shared/gatekeeper.py` skeleton
- [x] Create `src/debate/shared/config.py` skeleton
- [x] Create `src/debate/shared/version.py` with `__version__`
- [x] Create `src/debate/shared/constants.py`
- [x] Create `src/debate/shared/logger.py` skeleton
- [x] Create `src/debate/shared/schemas.py` skeleton
- [x] Create `src/debate/shared/llm_provider/__init__.py`
- [x] Create `src/debate/shared/llm_provider/base.py` skeleton
- [x] Create `src/debate/shared/llm_provider/anthropic_provider.py` skeleton
- [x] Create `src/debate/shared/llm_provider/openai_provider.py` skeleton
- [x] Verify `uv run python -c "import debate"` succeeds (user to run)
- [x] Verify `uv run ruff check src` returns 0 errors (user to run)

### 2.4 Test scaffolding
- [x] Create `tests/__init__.py`
- [x] Create `tests/conftest.py` with placeholder fixtures
- [x] Create `tests/unit/__init__.py`
- [x] Create `tests/unit/test_smoke.py` with `assert True`-style tests
- [x] Create `tests/integration/__init__.py`
- [x] Verify `uv run pytest` discovers and runs tests (user to run)
- [ ] Verify `uv run pytest --cov` produces a coverage report (user to run)

### 2.5 Data + results directories
- [x] Create `data/dogs/` directory
- [x] Create `data/cats/` directory
- [x] Add `.gitkeep` to `data/dogs/`
- [x] Add `.gitkeep` to `data/cats/`
- [x] Create `results/` directory
- [x] Add `results/.gitkeep`
- [x] Update `.gitignore` to ignore `data/*/chroma/` (vector store binary files)
- [x] Update `.gitignore` to ignore `results/logs/` (log output)

---

## Phase 3 — Core Code (Stage 3 part 1: agents + orchestrator)

### 3.1 Schemas (`shared/schemas.py`) ✅
- [x] Define `Side = Literal["dogs", "cats"]` type alias
- [x] Define `ChatMessage` Pydantic model (role, content)
- [x] Define `Ping` Pydantic model (round, side, text, citations, refers_to_ping, timestamp, tokens_in, tokens_out)
- [x] Define `Score` Pydantic model (ping_round, side, structure, logos, pathos, ethos, clash, rationale)
- [x] Define `Verdict` Pydantic model (winner, dogs_total, cats_total, margin, written_rationale, key_points_dogs, key_points_cats)
- [x] Define `DebateResult` Pydantic model
- [x] Define `OpeningBrief` Pydantic model
- [x] Define `YourTurn` Pydantic model
- [x] Define `Ready` envelope
- [x] Define `CompletionResponse` Pydantic model
- [x] Define `MessageEnvelope` union type
- [x] Add `model_config` ConfigDict with `extra = "forbid"` to envelopes
- [x] Write `test_schemas.py` — Ping round-trip JSON
- [x] Write `test_schemas.py` — Score round-trip JSON
- [x] Write `test_schemas.py` — Verdict round-trip JSON
- [x] Write `test_schemas.py` — invalid side rejected
- [x] Write `test_schemas.py` — extra field rejected

### 3.2 Config loader (`shared/config.py`) ✅
- [x] Define `SetupConfig` Pydantic model mirroring setup.json
- [x] Define `RateLimitConfig` Pydantic model
- [x] Define `LoggingConfig` Pydantic model
- [x] Implement `load_setup(path) -> SetupConfig`
- [x] Implement `load_rate_limits(path) -> RateLimitConfig`
- [x] Implement `load_logging(path) -> LoggingConfig`
- [x] Implement `validate_version(cfg, expected="1.00")` helper
- [x] Implement `load_env(dotenv_path=".env")` that calls dotenv
- [x] Write `test_config_loads_setup`
- [x] Write `test_config_loads_rate_limits`
- [x] Write `test_config_loads_logging`
- [x] Write `test_config_rejects_wrong_version`
- [x] Write `test_config_missing_file_raises`

### 3.3 LLM Provider abstraction ✅
- [x] Define `LLMProvider` ABC in `base.py`
- [x] Define `CompletionResponse` (already in schemas, re-export)
- [x] Implement `AnthropicProvider.complete(...)`
- [x] Implement `AnthropicProvider` token field mapping from `response.usage`
- [x] Implement `AnthropicProvider` cache_control marking on system + first messages
- [x] Implement `AnthropicProvider` raise on missing `ANTHROPIC_API_KEY`
- [x] Implement `OpenAIProvider.complete(...)`
- [x] Implement `OpenAIProvider` system-prompt-as-first-message conversion
- [x] Implement `OpenAIProvider` token field mapping (prompt_tokens / completion_tokens)
- [x] Implement `OpenAIProvider` raise on missing `OPENAI_API_KEY`
- [x] Implement `build_provider(name) -> LLMProvider` factory
- [x] Implement provider registry (dict of name → class)
- [x] Write `test_provider_registry_known`
- [x] Write `test_provider_registry_unknown_raises`
- [x] Write `test_anthropic_provider_mock_call` (mocked SDK)
- [x] Write `test_anthropic_provider_token_extraction`
- [x] Write `test_anthropic_provider_cache_headers_set`
- [x] Write `test_openai_provider_mock_call`
- [x] Write `test_openai_provider_token_extraction`
- [x] Write `test_provider_missing_env_var_raises`

### 3.4 Base agent (`agents/base_agent.py`) ✅
- [x] Define `BaseAgent` ABC
- [x] Constructor: id, system_prompt, provider, gatekeeper, logger, model_name
- [x] Attribute: `history: list[ChatMessage]`
- [x] Method: `_append_user(content)`
- [x] Method: `_append_assistant(content)`
- [x] Method: `generate(user_message) -> CompletionResponse` (calls gatekeeper-wrapped provider)
- [x] Method: `receive(envelope)` (abstract)
- [x] Method: `run(inbox_queue, outbox_queue)` (process main loop)
- [x] Method: `heartbeat(out_queue)`
- [x] Write `test_base_agent_history_append`
- [x] Write `test_base_agent_generate_uses_gatekeeper` (mocked)
- [x] Write `test_base_agent_history_disjoint_per_instance`

### 3.5 Debate agent base (Dogs + Cats common) ✅
- [x] Define `DebateAgent(BaseAgent)` abstract subclass
- [x] Attribute: `rag: RAGStore | None`
- [x] Attribute: `search_tool: WebSearch`
- [x] Method: `_collect_evidence(query) -> dict` (search + RAG)
- [x] Method: `_build_user_prompt(opening_brief, previous_ping, evidence) -> str`
- [x] Method: `_parse_ping_json(text) -> Ping`
- [x] Method: `_validate_clash(ping, previous_ping)` (round ≥ 2)
- [x] Method: `handle_your_turn(envelope) -> Ping`
- [x] Override `receive(envelope)` to route by envelope type
- [x] Write `test_debate_agent_parse_valid_json`
- [x] Write `test_debate_agent_parse_invalid_json_raises`
- [x] Write `test_debate_agent_clash_missing_raises`
- [x] Write `test_debate_agent_collect_evidence_calls_search_and_rag`

### 3.6 Dogs agent ✅
- [x] Load `dogs_system_prompt.md` from `prompts/` directory at construction
- [x] Write `prompts/dogs_system_prompt.md` (logos/ethos persona)
- [x] Implement `DogsAgent(DebateAgent)` with side="dogs"
- [x] Override search query phrasing (add "study", "research", "longevity", etc.)
- [x] Override RAG collection name → "dogs"
- [x] Write `test_dogs_agent_side_is_dogs`
- [x] Write `test_dogs_agent_loads_system_prompt`
- [x] Write `test_dogs_agent_search_query_adds_authority_keywords`

### 3.7 Cats agent ✅
- [x] Write `prompts/cats_system_prompt.md` (pathos/Socratic persona)
- [x] Implement `CatsAgent(DebateAgent)` with side="cats"
- [x] Override search query phrasing (add "literature", "philosophy", "culture")
- [x] Override RAG collection name → "cats"
- [x] Write `test_cats_agent_side_is_cats`
- [x] Write `test_cats_agent_loads_system_prompt`
- [x] Write `test_cats_agent_search_query_adds_literary_keywords`

### 3.8 Judge agent ✅
- [x] Write `prompts/judge_system_prompt.md` (5-dim rubric)
- [x] Implement `JudgeAgent(BaseAgent)` (no RAG, no search)
- [x] Method: `score_ping(ping) -> Score`
- [x] Method: `decide_winner(scores, pings) -> Verdict`
- [x] Method: `_tie_break(dogs_total, cats_total, scores) -> Side`
- [x] Method: `_detect_collusion(recent_pings) -> bool`
- [x] Method: `_extract_key_points(pings_for_side) -> list[str]`
- [x] Method: `receive(envelope)` — route Ping → score, all-rounds-done → verdict
- [x] Write `test_judge_scores_ping_returns_valid_score`
- [x] Write `test_judge_tiebreak_uses_clash`
- [x] Write `test_judge_tiebreak_falls_through_to_pathos`
- [x] Write `test_judge_detects_repeated_concession`
- [x] Write `test_judge_verdict_never_ties`

### 3.9 Orchestrator (`services/orchestrator.py`) ✅
- [x] Class `Orchestrator(topic, num_rounds, ...)` — synchronous loop, process-spawn wrapping deferred (see PROMPTS.md 2026-05-22 entry)
- [ ] Method: `_spawn_agent(agent_cls, in_q, out_q) -> Process` — deferred to Phase 4 watchdog integration
- [x] Method: `_broadcast_opening_brief(dogs, cats, judge)`
- [ ] Method: `_wait_for_all_ready(queues, timeout)` — N/A in synchronous loop (deferred with process model)
- [x] Method: `_run_round(round_num, previous_ping) -> (dogs_ping, cats_ping)`
- [x] Method: `_collect_verdict(judge) -> Verdict`
- [x] Method: `_persist_result(result) -> Path`
- [x] Method: `run_debate() -> DebateResult`
- [ ] Graceful shutdown handler (SIGINT/SIGTERM) — added when process model lands
- [x] Write `test_orchestrator_run_debate_smoke` (3 mocked agents, 2 rounds)
- [x] Write `test_orchestrator_persists_result_json`
- [x] Write `test_orchestrator_dogs_opens_round_1`
- [x] Write `test_orchestrator_judge_receives_every_ping`

### 3.10 SDK (`sdk/sdk.py`) ✅
- [x] Class `DebateSDK(setup_path=..., gatekeeper=..., results_dir=...)`
- [x] Method: `run_debate(topic=None) -> DebateResult`
- [x] Method: `get_last_verdict() -> Verdict | None`
- [x] Method: `get_cost_report() -> dict`
- [x] Method: `list_past_debates() -> list[Path]`
- [x] Internal: wires orchestrator + (passthrough) gatekeeper together — real gatekeeper drops in at Phase 4.1
- [x] Write `test_sdk_run_debate_returns_result`
- [x] Write `test_sdk_get_last_verdict_after_run`
- [x] Write `test_sdk_list_past_debates`
- [x] Write `test_sdk_passthrough_gatekeeper_default`

---

## Phase 4 — Engineering: Gatekeeper, Watchdog, Logging

### 4.1 Gatekeeper (`shared/gatekeeper.py`) ✅
- [x] Class `ApiGatekeeper(rate_config, setup, logger, cost_logger, sleep_fn)`
- [x] Attribute: per-service rolling-window counters (`RollingWindow` × minute + hour)
- [x] Attribute: per-service pending+in_flight counters with `threading.Lock`
- [x] Attribute: `CostTracker` (running totals by-model)
- [x] Method: internal rate check inside `_wait_for_slot`
- [x] Method: rate window add inside `_wait_for_slot`
- [x] Method: `compute_cost(...)` extracted to `pricing.py`
- [x] Method: cost-log JSONL via `log_cost_entry`
- [x] Method: `is_retryable(exc, codes)` (status code or TimeoutError/ConnectionError)
- [x] Method: linear backoff `retry_after_seconds * attempt`
- [x] Method: `execute(api_call, *args, service="default", **kwargs)`
- [x] Method: `get_queue_status(service) -> QueueStatus`
- [x] Method: `get_token_summary() -> dict`
- [x] Concurrency cap via `threading.Semaphore`
- [x] Budget alert at warning_threshold_pct (WARNING log, fires once)
- [x] Budget enforcement at hard_limit_pct (raise `BudgetExceededError`)
- [x] Exception classes: `BudgetExceededError`, `QueueFullError`, `ApiCallFailedError`
- [x] Pricing read from `config/setup.json.pricing` via `SetupConfig`
- [x] Persist cost log to `results/cost_log.jsonl` (when `cost_logger` provided)
- [x] Write `test_execute_returns_result` (≈ single call succeeds)
- [x] Write `test_execute_records_tokens_and_cost`
- [x] Write `test_execute_records_cache_tokens_separately`
- [ ] Write `test_gatekeeper_rate_limit_triggers_queue` — covered partially by `test_queue_full_raises` (queue depth path); full drain-after-window test deferred
- [x] Write `test_retries_on_retryable_then_succeeds` (covers 429/500/503 paths)
- [x] Write `test_max_retries_raises_api_call_failed`
- [x] Write `test_timeout_is_retried`
- [x] Write `test_concurrent_max_respected`
- [x] Write `test_budget_warning_logged_once`
- [x] Write `test_budget_exceeded_raises`
- [x] Write `test_queue_full_raises`
- [x] Write `test_cost_logger_called_when_provided` (≈ summary matches log)
- [ ] Write `test_gatekeeper_cybersecurity_sanitize_called` — deferred (sanitize hook in PRD §9 not yet implemented; will land if a sanitizer becomes needed)

### 4.2 Watchdog (`services/watchdog.py`) ✅
- [x] Class `Watchdog(config, logger, clock, sleep_fn)`
- [x] Attribute: per-agent `_Entry` with `last_seen` (monotonic float)
- [x] Attribute: per-agent `restart_count`
- [x] Attribute: per-agent `restart_fn`
- [x] Attribute: `threading.Lock` around `_entries`
- [x] Method: `register(agent_id, process, restart_fn)`
- [x] Method: `heartbeat(agent_id)` (records last_seen safely)
- [x] Method: `_loop()` daemon-thread loop
- [x] Method: `check_once()` — deterministic single pass (exposed for testing)
- [x] Method: `_handle_timeout(agent_id, entry)` — terminate + restart
- [x] Method: `start()` / `stop()`
- [x] Exception: `WatchdogFatalError` after `max_restarts_per_agent` exceeded
- [ ] SIGINT/SIGTERM clean shutdown — deferred to orchestrator process-model wiring (Phase 4 →orchestrator multi-process upgrade)
- [x] Write `test_healthy_run_no_restart`
- [x] Write `test_detects_timeout_and_invokes_restart`
- [x] Write `test_max_restarts_raises_fatal` + `test_fatal_agent_skipped_on_next_check`
- [x] Write `test_stop_terminates_registered_processes`
- [x] Write `test_heartbeat_after_register_resets_last_seen` + `test_unknown_heartbeat_is_safe` (concurrency safety covered via lock — full multi-thread test deferred until orchestrator goes multiprocess)
- [x] Write `test_restart_fn_exception_does_not_propagate`
- [x] Write `test_config_from_timeouts`

### 4.3 Logger (`shared/logger.py`) ✅
- [x] Class `FifoRotatingHandler(logging.Handler)` (custom)
- [x] Logic: cap N files, M lines each, rotate FIFO (delete oldest)
- [x] Counter: per-file line count
- [x] Format: ISO-timestamp + level + module + message
- [x] JSON-structured option for cost log (`get_cost_logger` + `log_cost_entry`)
- [x] Function: `get_logger(name, config) -> logging.Logger`
- [x] Function: `configure_root_logger(config)`
- [x] Write `test_logger_rotation_at_max_lines`
- [x] Write `test_logger_deletes_oldest_at_max_files`
- [x] Write `test_logger_writes_iso_timestamp`
- [ ] Write `test_logger_multiprocessing_safe` (queue-based handler) — deferred to Phase 4.2 when process model lands
- [x] Write `test_logger_respects_level_from_config`

### 4.4 Web search (`services/tools/web_search.py`) ✅
- [x] Class `WebSearch(gatekeeper, backend=None, timeout_seconds, logger)`
- [x] Method: `search(query, max_results=5) -> list[SearchResult]`
- [x] Define `SearchResult` Pydantic model (title, url, snippet)
- [x] DuckDuckGo backend implementation (`DDGBackend` using `duckduckgo_search.DDGS`)
- [ ] Tavily fallback implementation (behind feature flag) — deferred; not needed unless DDG rate-limits us during real runs
- [x] Route through `gatekeeper.execute(..., service="search")`
- [x] Timeout per request from config (passed into `DDGBackend(timeout=...)`)
- [x] Handle empty results gracefully (returns `[]` on empty query OR backend exception)
- [x] Write `test_search_returns_results` (mocked backend)
- [x] Write `test_search_empty_query_short_circuits`
- [x] Write `test_search_swallows_backend_errors`
- [x] Write `test_search_routes_through_gatekeeper`
- [x] Write `test_search_handles_missing_fields`

### 4.5 Constants (`shared/constants.py`) ✅
- [x] Define `DEFAULT_CONFIG_DIR = Path("config")`
- [x] Define `DEFAULT_RESULTS_DIR = Path("results")`
- [x] Define `DEFAULT_DATA_DIR = Path("data")`
- [x] Define `MessageType` enum (OPENING_BRIEF, READY, YOUR_TURN, PING, VERDICT, HEARTBEAT, COLLUSION_WARNING)
- [x] Define `SIDE_DOGS = "dogs"` / `SIDE_CATS = "cats"` literals
- [x] Define `DEFAULT_MAX_TOKENS = 1024`

---

## Phase 5 — RAG

### 5.1 Embedder (`services/rag/embedder.py`)
- [ ] Class `Embedder(model_name)`
- [ ] Lazy-load sentence-transformers model on first call
- [ ] Method: `embed_text(text) -> list[float]`
- [ ] Method: `embed_batch(texts) -> list[list[float]]`
- [ ] Cache loaded model at class level (singleton)
- [ ] Write `test_embedder_returns_correct_dim`
- [ ] Write `test_embedder_batch_matches_single_calls`
- [ ] Write `test_embedder_idempotent_for_same_text`

### 5.2 RAG store (`services/rag/rag_store.py`)
- [ ] Class `RAGStore(collection_name, persist_dir, embedder)`
- [ ] Initialize ChromaDB persistent client
- [ ] Create/get collection per agent
- [ ] Method: `add(documents, metadatas, ids)`
- [ ] Method: `retrieve(query, k=3) -> list[Passage]`
- [ ] Define `Passage` Pydantic model (text, metadata, distance)
- [ ] Method: `count() -> int`
- [ ] Method: `clear()`
- [ ] Write `test_rag_store_add_then_retrieve`
- [ ] Write `test_rag_store_retrieve_k_results`
- [ ] Write `test_rag_store_empty_returns_empty_list`
- [ ] Write `test_rag_store_isolated_per_collection`
- [ ] Write `test_rag_store_persists_across_reload`

### 5.3 Ingest (`services/rag/ingest.py`)
- [ ] CLI entrypoint with `--agent {dogs,cats}` flag
- [ ] Read all `.txt` files in `data/<agent>/`
- [ ] Parse YAML frontmatter from each file
- [ ] Chunk body to `chunk_size` words (configurable)
- [ ] Embed each chunk
- [ ] Build deterministic ID (file path + chunk index hash)
- [ ] Idempotent insert (skip existing IDs)
- [ ] Log summary: N files, M chunks added, K skipped
- [ ] Write `test_ingest_loads_all_files`
- [ ] Write `test_ingest_parses_frontmatter`
- [ ] Write `test_ingest_chunks_at_size`
- [ ] Write `test_ingest_second_run_is_noop`
- [ ] Write `test_ingest_missing_frontmatter_raises`

### 5.4 Dogs corpus (`data/dogs/`)
- [ ] Source: companion-animal longevity study summary (1 passage)
- [ ] Source: cardiovascular health & dog ownership (1 passage)
- [ ] Source: working dogs in search-and-rescue stats (1 passage)
- [ ] Source: service dogs for disability (1 passage)
- [ ] Source: dog walking & physical activity research (1 passage)
- [ ] Source: canine cognition (Stanley Coren) (1 passage)
- [ ] Source: dog domestication history (1 passage)
- [ ] Source: dog ownership rates worldwide (1 passage)
- [ ] Source: therapy dogs in hospitals (1 passage)
- [ ] Source: police K-9 effectiveness (1 passage)
- [ ] Source: AHA statement on pets (1 passage)
- [ ] Source: study on owner mortality & dogs (1 passage)
- [ ] Source: children's social development & dogs (1 passage)
- [ ] Source: famous dogs in history (Laika, Balto) (1 passage)
- [ ] Source: military working dog history (1 passage)
- [ ] Add YAML frontmatter to all 15 passages
- [ ] Cross-check each ≤ 300 words

### 5.5 Cats corpus (`data/cats/`)
- [ ] Source: Hemingway and his polydactyl cats (1 passage)
- [ ] Source: Ancient Egyptian reverence — Bastet (1 passage)
- [ ] Source: T.S. Eliot, Old Possum's Practical Cats (1 passage)
- [ ] Source: Montaigne on cats and play (1 passage)
- [ ] Source: Schopenhauer on solitude (1 passage)
- [ ] Source: Maneki-neko Japanese cultural significance (1 passage)
- [ ] Source: Istanbul street cats / Turkish culture (1 passage)
- [ ] Source: cat in Chinese art & poetry (1 passage)
- [ ] Source: stress reduction & cat ownership study (1 passage)
- [ ] Source: childhood allergy & early cat exposure study (1 passage)
- [ ] Source: cat purr frequencies & healing claim (1 passage)
- [ ] Source: feral cat ecology / ecological balance (1 passage)
- [ ] Source: Murakami on cats in his fiction (1 passage)
- [ ] Source: Charles Baudelaire, "Les Chats" (1 passage)
- [ ] Source: independence as philosophical virtue (1 passage)
- [ ] Add YAML frontmatter to all 15 passages
- [ ] Cross-check each ≤ 300 words

### 5.6 Wire RAG into agents
- [ ] Modify `DebateAgent.__init__` to optionally take a `rag: RAGStore`
- [ ] Modify `_collect_evidence` to call `rag.retrieve` and include passages
- [ ] Include RAG citations in `Ping.citations` field
- [ ] Add config flag `rag_enabled` per agent in setup.json
- [ ] Write `test_debate_agent_uses_rag_when_provided`
- [ ] Write `test_debate_agent_skips_rag_when_disabled`
- [ ] Write `test_debate_agent_rag_citations_in_ping`

---

## Phase 6 — Tests, Coverage, CI

### 6.1 Integration tests (`tests/integration/`)
- [ ] `test_full_debate_smoke.py` — full debate with mocked LLM, 2 rounds, assert winner declared
- [ ] `test_full_debate_10_rounds.py` — full 10-round with mocked LLM, assert ping count + verdict
- [ ] `test_full_debate_with_rag.py` — full debate with real RAG (small fixture corpus)
- [ ] `test_full_debate_handles_judge_invalid_json.py` — judge returns bad JSON twice then valid
- [ ] `test_full_debate_handles_agent_timeout.py` — agent hangs, watchdog restarts
- [ ] `test_full_debate_budget_exceeded_aborts_cleanly.py`
- [ ] `test_persists_debate_result_to_disk.py`
- [ ] `test_two_debates_in_sequence.py` (memory isolation between runs)

### 6.2 Coverage hardening
- [ ] Run `uv run pytest --cov` and capture baseline percentage
- [ ] Identify uncovered branches in `gatekeeper.py` and add tests
- [ ] Identify uncovered branches in `watchdog.py` and add tests
- [ ] Identify uncovered branches in `orchestrator.py` and add tests
- [ ] Identify uncovered branches in `judge_agent.py` and add tests
- [ ] Identify uncovered branches in `rag_store.py` and add tests
- [ ] Cover all 4 envelope types in `base_agent.receive`
- [ ] Cover all 4 retry HTTP codes in gatekeeper
- [ ] Cover both tie-break paths in judge
- [ ] Reach ≥ 85% total coverage
- [ ] Document any intentional omits in `pyproject.toml` `[tool.coverage.run] omit`

### 6.3 Ruff zero-violations sweep
- [ ] Run `uv run ruff check .` and capture errors
- [ ] Fix all E (style) errors
- [ ] Fix all F (pyflakes) errors
- [ ] Fix all I (import sort) errors
- [ ] Fix all N (naming) errors
- [ ] Fix all UP (pyupgrade) errors
- [ ] Fix all B (bugbear) errors
- [ ] Fix all C4 (comprehensions) errors
- [ ] Fix all SIM (simplification) errors
- [ ] Final `uv run ruff check .` returns 0 errors
- [ ] Final `uv run ruff format --check .` clean

### 6.4 File-size sweep
- [ ] Audit every `.py` file in `src/` for ≤ 150 LOC (excluding blank + comments)
- [ ] Refactor any file > 150 LOC by extracting helpers or mixins
- [ ] Audit every test file for ≤ 150 LOC
- [ ] Document the audit in `docs/PROMPTS.md` as an entry

### 6.5 Mocking + fixtures
- [ ] Add `MockLLMProvider` fixture for fast tests
- [ ] Add `MockGatekeeper` fixture
- [ ] Add `MockRAGStore` fixture with seeded passages
- [ ] Add `MockWebSearch` fixture
- [ ] Add `tmp_chroma_dir` fixture
- [ ] Add `sample_setup_config` fixture
- [ ] Add `sample_ping` factory fixture
- [ ] Add `sample_score` factory fixture

### 6.6 Continuous quality
- [ ] Add `Makefile` or `justfile` with targets: `test`, `lint`, `format`, `cov`, `run`
- [ ] Document test-running command in `README.md` (Phase 7)
- [ ] Confirm `uv run pytest --cov` passes with `fail_under = 85`
- [ ] Confirm `uv run ruff check .` passes with `exit 0`

---

## Phase 7 — Polish: terminal menu, README, notebook, screenshots

### 7.1 Terminal menu (`src/debate/main.py`)
- [ ] Implement `cli()` entry point
- [ ] Menu loop: print options, read keypress, dispatch
- [ ] Option 1: "Run debate" → `sdk.run_debate()`
- [ ] Option 2: "View last verdict" → pretty-print verdict
- [ ] Option 3: "View cost report" → pretty-print cost summary
- [ ] Option 4: "List past debates" → file listing
- [ ] Option 5: "Open a past debate" → file picker, show transcript
- [ ] Option Q: Quit
- [ ] Pretty-print Ping (round, side, text, citations)
- [ ] Pretty-print Verdict (winner, totals, rationale)
- [ ] Pretty-print Score breakdown table
- [ ] Color output via `rich` (optional dep) or plain
- [ ] Handle Ctrl-C gracefully (clean shutdown)
- [ ] Write `test_main_menu_quit_exits`
- [ ] Write `test_main_menu_run_debate_calls_sdk`
- [ ] Take screenshot of menu in terminal
- [ ] Save screenshot to `assets/terminal_menu.png`

### 7.2 README (`README.md`)
- [ ] Section: project title + tagline
- [ ] Section: badges (if any — Python version, license)
- [ ] Section: TL;DR (3-sentence summary)
- [ ] Section: system requirements
- [ ] Section: installation — `uv sync`
- [ ] Section: configuration — copy `.env.example` to `.env`, fill key
- [ ] Section: running — `uv run python -m debate`
- [ ] Section: terminal menu screenshot
- [ ] Section: architecture diagram (link to PLAN.md or embed)
- [ ] Section: Stage 1 manual transcript (from Phase 1 deliverable)
- [ ] Section: example output — sample verdict + cost report
- [ ] Section: configuration file reference (setup.json, rate_limits.json)
- [ ] Section: how to swap LLM provider
- [ ] Section: how to add RAG passages
- [ ] Section: test instructions — `uv run pytest --cov`
- [ ] Section: lint instructions — `uv run ruff check .`
- [ ] Section: cost analysis table (from a real run)
- [ ] Section: contribution guidelines
- [ ] Section: license (MIT or course-required)
- [ ] Section: credits / acknowledgments (Dr. Yoram Segal, partner, AI assistance)
- [ ] Section: known limitations / out-of-scope
- [ ] Section: troubleshooting
- [ ] Add 4+ screenshots: menu, mid-debate, verdict, cost report
- [ ] README ≤ N chars (no hard limit, but reasonable)

### 7.3 Analysis notebook (`notebooks/analysis.ipynb`)
- [ ] Cell 1: imports + load latest debate result
- [ ] Cell 2: pretty-print verdict
- [ ] Cell 3: bar chart — Dogs vs Cats total scores
- [ ] Cell 4: stacked bar — score breakdown per dimension per side
- [ ] Cell 5: heatmap — score per round per dimension per side
- [ ] Cell 6: line chart — clash score evolution across rounds
- [ ] Cell 7: word-count distribution per side
- [ ] Cell 8: cost breakdown — table by model with input/output tokens + $
- [ ] Cell 9: cache hit ratio over time
- [ ] Cell 10: parameter sensitivity — re-run debate with different temperature, compare verdicts
- [ ] Cell 11: latex equation for cost formula
- [ ] Cell 12: conclusion + key takeaways
- [ ] Export figures as `assets/*.png` for README
- [ ] Document notebook usage in README

### 7.4 Cost analysis table for submission
- [ ] Run a full real debate end-to-end
- [ ] Capture cost log
- [ ] Build the Table 4 (from §11 of the source PDF) markdown table
- [ ] Add table to `docs/PROMPTS.md` or a new `docs/COSTS.md`
- [ ] Document the optimization strategies used (caching, model choice, ping cap)
- [ ] Estimate token cost per "ping economy" trade-off

### 7.5 Class diagram artifact
- [ ] Render class diagram as PlantUML or Mermaid in `assets/class_diagram.svg`
- [ ] Link from `PLAN.md` and `README.md`

---

## Phase 8 — Submission

### 8.1 Final integration check
- [ ] Fresh clone of repo into a temp directory
- [ ] `uv sync` works on fresh clone
- [ ] `.env.example` → `.env` with real key
- [ ] `uv run pytest --cov` passes ≥ 85%
- [ ] `uv run ruff check .` passes 0 errors
- [ ] `uv run python -m debate` launches the menu
- [ ] A full debate runs end-to-end without errors
- [ ] `results/debates/<timestamp>.json` is produced
- [ ] Verdict declares a non-tie winner
- [ ] Cost report shows < $5 spent

### 8.2 Repo hygiene
- [ ] No `.env` in git history (`git log --all -- .env`)
- [ ] No API keys in any committed file (grep sweep)
- [ ] `.gitignore` covers all sensitive paths
- [ ] All TODO items in PRD/PLAN resolved or moved to "out of scope"
- [ ] All `# TODO:` / `# FIXME:` comments in code resolved or filed as issues
- [ ] All ADRs in PLAN.md final (no "decision pending")
- [ ] `docs/PROMPTS.md` updated with final entries

### 8.3 Submission package
- [ ] Generate PDF of README (or specific submission doc) for Moodle
- [ ] Verify GitHub repo is public OR shared with lecturer
- [ ] Verify partner has same repo link
- [ ] Both partners upload PDF to Moodle with same repo URL
- [ ] Tag release `v1.0.0` on GitHub
- [ ] Final commit: "Ready for submission"
- [ ] Push final commit + tag to GitHub
- [ ] Sanity-check from a new browser session: repo loads, README displays, files visible

### 8.4 Last-minute items
- [ ] Confirm debate transcripts are in English or Hebrew (not Arabic)
- [ ] If pings reduced to 5 instead of 10 — explicit note in README
- [ ] No `__pycache__/`, `.venv/`, or other build artifacts committed
- [ ] LICENSE file present
- [ ] Pair submission confirmed by both partners
- [ ] Receipt confirmation from Moodle saved

---

## Notes
- This list will grow as we discover edge cases. New tasks go in the appropriate phase section. Cross-cutting concerns can use a new "Phase X.Y" subsection.
- Tasks marked `[x]` are complete. `🟨` next to a section header means "in progress."
- Per CLAUDE.md §3, no code begins until PRD + PLAN + this TODO are approved by both partners.
