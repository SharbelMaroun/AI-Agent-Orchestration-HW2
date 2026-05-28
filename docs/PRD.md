# Product Requirements Document — AI Agent Debate (HW2)

**Project:** AI-Agent-Orchestration-HW2 · **Topic:** Cats vs Dogs as the better pet
**Version:** 1.00 · **Status:** Approved (spec stable; mid-implementation deltas tracked in `docs/TODO.md`)
**Authors:** Sharbel Maroun + Amr Safadi

---

## 1. Project Overview

### 1.1 Context
Coursework for "Orchestration of AI Agents." Exercise 02 from Dr. Yoram Segal's Lesson 05. Demonstrates the canonical agent architecture (LLM + Context Window + Tools + RAG), inter-process communication, and orchestration of multiple autonomous agents under a supervisor.

### 1.2 Goal
Build a debate between three AI agents under Python orchestration:
- **Judge Agent** (parent) — moderates, scores, declares a winner.
- **Dogs Agent** — defends "Dogs are the better pet" using logos + ethos.
- **Cats Agent** — defends "Cats are the better pet" using pathos + Socratic style.

The Judge declares a winner based on **persuasive ability**, not factual truth. **Ties are forbidden.**

### 1.3 Target Audience
- Course examiner (Dr. Yoram Segal)
- Lecturer for grading per submission rubric
- Course peers as code reviewers

### 1.4 Why Cats vs Dogs?
- Normative topic with no empirical ground truth — winner decided by rhetoric.
- Symmetric: both sides have rich material (studies, history, culture).
- Universally familiar — judge needs no expertise.
- Safe — no political/religious/protected-class risk.
- Web search returns abundant material for both sides without resolving the debate.

---

## 2. Goals & Acceptance Criteria

### 2.1 Functional KPIs
| # | Goal | Acceptance Criterion |
|---|---|---|
| G1 | Run a full debate end-to-end | `python -m debate` produces a complete debate log + verdict file |
| G2 | Each side argues ≥ 10 pings | Exactly 10 Pro + 10 Con pings (= 20 LLM calls per side) before verdict |
| G3 | Mutual reference enforced | Each ping references the opponent's previous ping (clash score > 0) |
| G4 | Judge declares a winner | No tie; verdict includes side, score breakdown, written rationale |
| G5 | Different rhetorical styles | Pro-Dogs system prompt ≠ Pro-Cats; loaded from separate Skill files |
| G6 | Web search used | Every Pro/Con ping calls the search tool ≥ 1 time |
| G7 | RAG used | Every Pro/Con ping retrieves ≥ 1 chunk from its corpus |
| G8 | JSON IPC | All inter-process messages are valid JSON, schema-validated |
| G9 | Anti-collusion | Judge penalizes concessions without rebuttal |
| G10 | Process supervision | Watchdog kills + restarts stuck child after `timeout_seconds` |

### 2.2 Non-Functional KPIs
| # | Metric | Threshold |
|---|---|---|
| N1 | Test coverage | ≥ 85% |
| N2 | Ruff violations | 0 |
| N3 | File length | ≤ 150 LOC per file |
| N4 | Hardcoded values | 0 (everything in `config/` or env) |
| N5 | Secrets in repo | 0 (only `.env-example`) |
| N6 | Token spend per full debate | Logged + summarized; alert if > budget |

---

## 3. Functional Requirements

### 3.1 Architecture (mandatory)
- **3 agents:** Judge, Dogs, Cats — each a Python class wrapping an LLM call with a distinct system prompt.
- **Process model:** Python `multiprocessing` (3 child processes). See PLAN.md ADR-001.
- **Message flow:** `Judge → Dogs → Judge → Cats → Judge` for every round. No direct Dogs ↔ Cats communication.
- **IPC:** JSON messages via `multiprocessing.Queue`.

### 3.2 The Debate Loop
1. **Setup:** Orchestrator spawns Dogs, Cats, Judge processes. Each loads its system prompt.
2. **Opening brief:** Orchestrator broadcasts `OPENING_BRIEF` (topic, rules, num_rounds, agent's own side, rubric for Judge).
3. **Round 1:** Orchestrator flips a coin for Dogs/Cats opener, then signals the opener with `YOUR_TURN { previous_ping: null }`.
4. **Routing + scoring:** The opener's ping goes to Judge. Judge scores it. The opponent receives `YOUR_TURN { previous_ping: <opener ping> }`.
5. The second side produces ping #1 (must clash with opener #1). Judge scores. The next round continues in the same alternating order.
6. Repeat steps 3–5 until **10 rounds × 2 sides = 20 pings** complete.
7. **Verdict:** Judge synthesizes all scores, identifies key points per side, writes rationale, declares winner. Emits `VERDICT` to Orchestrator. Orchestrator persists `DebateResult` JSON.

### 3.2.1 Synchronization Invariant
- **Exactly one agent is active at any moment.** The other two block on `queue.get()`.
- Agents cannot speak out of turn — they must receive a `YOUR_TURN` message before producing a ping.
- **Opening side is coin-flipped** (`1 → Dogs`, `0 → Cats`) and announced before round 1.
- The dialogue order from the transcript reader's perspective is strictly alternating once the opener is chosen. The Judge does not produce debate text — it only routes and scores between pings.
- All inter-process messages flow through the Orchestrator + Judge. **No direct Dogs ↔ Cats communication.** (Lesson 05 §8 rule #7.)

### 3.2.2 Agent Memory Model
- The LLM API is **stateless** (true for Anthropic, OpenAI, and other providers we abstract over): each call must include the full conversation history to give the model context.
- Each agent maintains its **own** in-memory `history: list[ChatMessage]` (system prompt + alternating user/assistant turns).
- Per-round, the agent appends the new `YOUR_TURN { previous_ping }` to its history, calls `provider.complete(...)` (which the Gatekeeper wraps), appends the assistant response, and emits the parsed ping.
- The three histories are **disjoint**: Dogs never sees Judge's scores or Cats' internal reasoning. Each agent only sees what the protocol explicitly sends it (its own outputs + opponent's pings, paraphrased).
- **Prompt caching** (Anthropic-specific feature; other providers may add equivalents) is enabled when the active provider supports it, to amortize the cost of re-sending growing histories — see `docs/PRD_gatekeeper.md` §9a and ADR-008 in `docs/PLAN.md`.

### 3.3 Judge Rubric (per ping, 0–3 each, max 15)
| Dimension | What it scores | Source |
|---|---|---|
| Structure | Claim + evidence + warrant present (Toulmin) | Toulmin model |
| Logos | Logical soundness, internal consistency | Aristotle |
| Pathos | Emotional resonance, vivid imagery | Aristotle / IBM Project Debater |
| Ethos | Credibility, sourcing, tone | Aristotle |
| Clash | Engaged opponent's previous argument | NSDA / Anti-collusion |

Final winner = higher total score; written rationale is mandatory.

### 3.4 Agent Personas (different Skills)
- **Dogs agent (logos/ethos):** formal tone, cites studies and statistics, appeals to authority (working dogs, longevity research, public health). RAG corpus = scientific articles, surveys, expert quotes. JSON `side: "dogs"`.
- **Cats agent (pathos/Socratic):** witty, philosophical, uses vivid imagery and reframing questions. RAG corpus = literary quotes, cultural history, philosophical essays. JSON `side: "cats"`.
- **Judge:** neutral evaluator, no expertise on cats or dogs, applies rubric mechanically. No RAG.

### 3.5 Required Tools
- **Web Search** — mandatory tool, available to Dogs and Cats (not Judge).
- **RAG** — optional per spec but **included in this project**. Dogs and Cats each have a private vector store. Judge has none.

### 3.6 Communication Format
All IPC messages: JSON with versioned schema. See `docs/PRD_judge.md` §schema.

---

## 4. Non-Functional Requirements

### 4.1 Engineering (from CLAUDE.md + Lesson 05)
- **Gatekeeper** — single chokepoint for all LLM/web/embedding API calls. Rate-limits, retries, queues, logs token usage, computes cost per model. See `docs/PRD_gatekeeper.md`.
- **Watchdog** — keep-alive pings every `heartbeat_seconds`. Kills + restarts unresponsive agents. See `docs/PRD_watchdog.md`.
- **Timeouts** — every external call has a configurable timeout.
- **SDK layer** — sole entry point for business logic. CLI / future UI / API all delegate to `debate.sdk`.
- **Built-in logging** — FIFO rotation, configured in `config/logging_config.json` (e.g., 20 files × 500 lines).
- **OOP** — class hierarchy with `BaseAgent` parent; shared logic in mixins or base. Class diagram in PLAN.md.
- **Configuration** — all parameters in `config/setup.json`, `config/rate_limits.json`, `config/logging_config.json`. Versioned (`"version": "1.00"`).
- **Secrets** — `ANTHROPIC_API_KEY` (or whichever provider) via `os.environ`. `.env` gitignored; only `.env-example` committed.
- **Package manager** — `uv` only. `pyproject.toml` + `uv.lock` committed.

### 4.2 Quality (from CLAUDE.md)
- TDD: tests written before/with code. Coverage ≥ 85%.
- Ruff: 0 violations. Config in `pyproject.toml`.
- All files ≤ 150 LOC.
- Comments explain *why*, not *what*. Docstrings on every public function.

### 4.3 UX
- **Terminal menu** mandatory — keyboard-driven (e.g., `1) Run debate  2) View last result  3) Quit`).
- Optional GUI with screenshots in README.

---

## 5. Assumptions, Dependencies, Constraints

### 5.1 Assumptions
- **LLM provider is configurable.** Default = OpenAI `gpt-4o-mini` for all three agents. The code uses an `LLMProvider` abstraction (see `PLAN.md` ADR-009) with three registered providers — `openai`, `google`, `anthropic` — selectable per-agent via `config/setup.json.models`.
- Web search tool = a free or low-cost provider (e.g., DuckDuckGo API, Tavily free tier).
- Embedding model for RAG = `sentence-transformers/all-MiniLM-L6-v2` (local, free) — independent of LLM provider choice.
- Vector store = ChromaDB (local, embedded, zero-setup).
- Python 3.10+ (per ruff config).
- Local development on Windows; cross-platform supported.

### 5.1a Environment Variables (`.env`)
Secrets are loaded from a `.env` file (gitignored) via `python-dotenv`. A committed `.env.example` documents every variable the project may read.

- `OPENAI_API_KEY` — required for the default config (all three agents use OpenAI).
- `ANTHROPIC_API_KEY` — required only if any agent's `provider` is set to `"anthropic"`.
- `OPENAI_API_KEY` — required only if any agent's `provider` is set to `"openai"`.
- `TAVILY_API_KEY` — optional, only if web search falls back to Tavily.

**One API key serves all three agents using the same provider.** Keys are account-level, not per-agent. If all three agents use OpenAI, only `OPENAI_API_KEY` is needed.

### 5.2 Dependencies (as installed)
- `google-generativeai` — Gemini provider (default)
- `anthropic` — Anthropic provider
- `openai` — OpenAI provider (default; install via `uv sync --extra openai`)
- `chromadb` — vector store
- `sentence-transformers` — embeddings
- `ddgs` — DuckDuckGo web search
- `pydantic` — JSON schema validation + `LLMProvider` types
- `python-dotenv` — env var loading
- `rich` — CLI menu rendering
- **Dev group:** `pytest` + `pytest-cov` + `ruff`
- **Package manager:** `uv`

### 5.3 Constraints
- **Budget:** soft cap configured in `config/setup.json`. Alert before exceeding.
- **Pings:** ≥ 10 per side OR ≥ 5 per side (must state in README + accept points deduction).
- **Pairs:** both members link the same repo on Moodle.
- **Language:** debate transcripts in English or Hebrew only.
- **Submission:** public GitHub recommended; inaccessible repo = disqualified.

### 5.4 Out of Scope
- Multi-topic support (Cats vs Dogs only).
- Real-time spectator UI (post-hoc transcript only).
- Multi-judge ensembles.
- Cross-LLM-provider redundancy.
- **Multimodal inputs:** the system is text-only. Agents do not consume or produce images, audio, or video. The only images in the project are README screenshots for documentation.

---

## 6. Phases & Timeline

PRD-level phases group the fine-grained `docs/TODO.md` phases. See `docs/TODO.md` for the ~600-task breakdown and per-sub-phase status.

| Phase | Deliverable | TODO phases | Status |
|---|---|---|---|
| 0 | Docs (this PRD + PLAN + per-mechanism PRDs + TODO + PROMPTS) | TODO Phase 0 | ✅ Complete |
| 2 | Single-Python-command debate (orchestrator + agents, no RAG/watchdog yet) | TODO Phase 2 + 3 | ✅ Complete |
| 3 | Add gatekeeper + watchdog + FIFO logs + tests | TODO Phase 4 + 6 | ✅ Complete (real SDK gatekeeper default; 92%+ coverage) |
| 4 | Add RAG + web search to Pro and Con | TODO Phase 5 | ✅ Complete (default SDK path wires DuckDuckGo + ChromaDB RAG) |
| 5 | Polish: terminal menu, README, analysis notebook, cost report | TODO Phase 7 | ✅ Complete; final process-mode real-run evidence captured |
| 6 | Submission: CI, pyproject.toml clean, public repo, Moodle PDF | TODO Phase 8 | ✅ Code gates, screenshots, docs, and evidence captured; Moodle upload remains the partner/admin step |

---

## 7. Acceptance Test (Final Submission)

The project passes if:
1. `uv sync --extra openai` then `uv run python -m debate` runs end-to-end on a fresh clone.
2. A full debate produces ≥ 10 pings per side, JSON-logged.
3. Judge declares a non-tie winner with rationale.
4. `uv run pytest --cov` reports ≥ 85% coverage and 0 failures.
5. `uv run ruff check` reports 0 violations.
6. No `.env`, API keys, or other secrets in the repo history.
7. README contains setup, usage, final evidence checklist, and cost analysis.
8. `docs/` contains PRD, PLAN, TODO, PROMPTS, and all per-mechanism PRDs.

---

## 8. References
- `Agents, Subagents, Commands and Skills_Summary.md` — Exercise 02 spec
- `CLAUDE.md` — Project engineering rules (Dr. Yoram Segal's submission guidelines)
- `hw2_Notes.txt` — Student notes
- Irving, Christiano, Amodei (2018), "AI Safety via Debate", arXiv:1805.00899
- Toulmin (1958), "The Uses of Argument"
- IBM Project Debater publications
- NSDA Lincoln-Douglas judging paradigms
