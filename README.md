# AI Agent Orchestration HW2 — Dogs vs Cats Debate

Three AI agents — **Dogs** (logos + ethos), **Cats** (pathos + Socratic), and a neutral **Judge** — conduct a 10-round structured debate on whether dogs or cats are the better pet. Persuasion wins; ties are forbidden.

[TL;DR](#tldr) · [Install](#installation) · [Usage](#usage) · [Architecture](#architecture) · [Tests](#tests--quality-gates) · [Costs](#cost-analysis)

---

## Authors

- **Sharbel Maroun** ([@SharbelMaroun](https://github.com/SharbelMaroun)) — `142183717+SharbelMaroun@users.noreply.github.com`
- **Amr Safadi** — `safadiamr02@gmail.com`

## Submission

- **Course:** Orchestration of AI Agents
- **Instructor:** Dr. Yoram Segal
- **Assignment:** Exercise 02 — AI Agent Debate
- **Topic:** *Are dogs or cats the better pet?* (judged on persuasive ability, not facts)
- **Repository:** public on GitHub (link in Moodle submission)
- **License:** MIT — see [LICENSE](LICENSE).

## TL;DR

Run `uv sync`, copy `.env.example` to `.env` and add `GOOGLE_API_KEY=...` (get one at https://aistudio.google.com/app/apikey), then `uv run python -m debate`. Choose option 1 from the menu and a full 10-round debate runs end-to-end, producing a JSON transcript under `results/debates/` and a winner declared by the Judge. **187 tests · 96.08% coverage · ruff 0 violations · format check clean.**

---

## Project summary

| Agent | Role | Style | Tools |
|---|---|---|---|
| **DogsAgent** | Argues dogs are the better pet | logos + ethos (studies, authority, statistics) | DuckDuckGo search, RAG corpus of 15 evidence-heavy passages |
| **CatsAgent** | Argues cats are the better pet | pathos + Socratic (vivid imagery, reframing) | DuckDuckGo search, RAG corpus of 15 literary/philosophical passages |
| **JudgeAgent** | Scores every ping, declares a non-tie winner | neutral, 5-dimension Toulmin/Aristotle rubric | none |

The Judge moderates all communication (no direct Dogs ↔ Cats). Every ping is JSON-validated, scored 0–3 across five dimensions (Structure, Logos, Pathos, Ethos, Clash), and the final verdict resolves any tie via a clash-then-pathos cascade. All LLM, search, and embedding calls funnel through a single `ApiGatekeeper` that enforces rate limits, retries with backoff, tracks token cost, and alerts on budget thresholds.

## Status

| Phase | Description | Status |
|---|---|---|
| 0 | Documentation & design | ✅ Complete |
| 1 | Manual debate (Stage 1 transcript) | ⬜ Partner-runnable — produces the `results/manual_stage1/` artifacts |
| 2 | Project bootstrap | ✅ Complete |
| 3 | Core code (schemas, providers, agents, orchestrator, SDK) | ✅ Complete |
| 4 | Engineering (gatekeeper, watchdog, logger, search) | ✅ Complete |
| 5 | RAG (embedder, store, ingest, 30 curated passages) | ✅ Complete |
| 6 | Tests + coverage ≥ 85% | ✅ Complete — **96.08%** (187 tests) |
| 7 | Polish (CLI menu, README full report, notebook, class diagram, Gemini provider, Skills restructure) | ✅ Complete |
| 8 | Submission (8.1 integration check ✅, 8.2 repo hygiene ✅) | 🟨 Automated checks done; awaiting real-API run + Moodle upload |

See `docs/TODO.md` for the full ~600-task breakdown.

**Deferred items** (each justified inline in `docs/TODO.md`):
- Orchestrator runs synchronously in one process; `multiprocessing.Process` spawning + SIGINT/SIGTERM clean shutdown land when the manual-debate Phase 1 transcript pins the exact concurrency expectations.
- Gatekeeper sanitize hook (PRD_gatekeeper §9) — not built; no incident class to defend against yet.
- Tavily web-search fallback — not built; `WebSearch.backend` is injectable so it drops in cleanly when needed.

---

## Installation

```powershell
# 1. Install dependencies (uses uv — see CLAUDE.md §11)
uv sync

# 2. Set up secrets
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=...   (default config uses Gemini)
# Get a key at https://aistudio.google.com/app/apikey
# To use Anthropic or OpenAI instead, edit config/setup.json.models
# and set the corresponding *_API_KEY in .env. See .env.example.

# 3. Ingest the RAG corpora (one-time per machine)
uv run python -m debate.services.rag.ingest --agent dogs
uv run python -m debate.services.rag.ingest --agent cats
# Or, with `just` installed: `just ingest`

# 4. Launch the debate menu
uv run python -m debate
# Or: `just run`
```

System requirements: Python ≥ 3.10 (developed on 3.13), `uv` package manager, ~500MB disk for the sentence-transformers embedding model (downloaded on first ingest), Windows / macOS / Linux.

## Usage

The CLI is a simple keyboard-driven menu:

```text
==============================================================
  AI Agent Orchestration HW2 — Dogs vs Cats Debate
==============================================================

  [1] Run a new debate
  [2] View last verdict
  [3] View cost report
  [4] List past debates
  [5] Open a past debate transcript
  [Q] Quit

Choose an option >
```

Screenshots: see [`assets/terminal_menu.png`](assets/terminal_menu.png) (added after first real-key run).

### Configuration

All knobs live in `config/` and are version-pinned (`"version": "1.00"`):

| File | What it controls |
|---|---|
| `config/setup.json` | Topic, num_rounds, max_words_per_ping, budget_usd, per-agent model selection, RAG/search settings, pricing table |
| `config/rate_limits.json` | Per-service rate limits, queue depths, retry policy, budget alert thresholds |
| `config/logging_config.json` | Log directory, format, FIFO rotation (N files × M lines), cost-log JSONL path |

### Swapping LLM providers

In `config/setup.json`, change any agent's `models.<agent>.provider` to a name registered in `src/debate/shared/llm_provider/__init__.py` (`anthropic` or `openai` ship; adding a provider is one new module + one registry line). Set the matching `*_API_KEY` in `.env`.

### Adding RAG passages

Drop a new `data/<side>/NN_title.txt` with YAML frontmatter (`source`, `type`, `relevance`) followed by `---` and the body. Re-run `uv run python -m debate.services.rag.ingest --agent <side>` — only the new chunks insert (`RAGStore.add` is idempotent).

---

## Architecture

Three-layer model: **SDK → Services → Shared**. Public consumers only talk to `DebateSDK`; the CLI is presentation only (CLAUDE.md §4).

```text
DebateSDK
   │
   ▼
Orchestrator ── runs round loop, persists DebateResult JSON
   │
   ├─► DogsAgent  ──► WebSearch ──┐
   ├─► CatsAgent  ──► RAGStore ──┤
   └─► JudgeAgent                 │
        ▲                         │
        └──── every API call ─────┴─► ApiGatekeeper ──► LLMProvider (Google / Anthropic / OpenAI)
                                       (rate, retry, cost, budget)
```

Full Mermaid class diagram + module map: see [`docs/PLAN.md`](docs/PLAN.md) §4 and §10.

### Synchronization invariant

Per PRD §3.2.1, exactly one agent speaks per turn and dialogue order is strictly **Dogs → Cats → Dogs → Cats → … → Dogs → Cats**. The Judge does not produce debate text — it only routes and scores between pings. Dogs always opens round 1.

### Judge rubric (per ping, 0–3 each, max 15)

| Dimension | What it scores | Source |
|---|---|---|
| Structure | Claim + evidence + warrant present | Toulmin model |
| Logos | Logical soundness, internal consistency | Aristotle |
| Pathos | Emotional resonance, vivid imagery | Aristotle / IBM Project Debater |
| Ethos | Credibility, sourcing, tone | Aristotle |
| Clash | Engaged opponent's previous argument | NSDA / anti-collusion |

Final winner = higher total; ties resolve via clash → pathos → structure cascade in `JudgeAgent._tie_break`.

---

## Tests & quality gates

```powershell
# Full suite with coverage
uv run pytest --cov           # or: just cov

# Lint
uv run ruff check .           # or: just lint

# CI bundle (lint + format-check + cov)
just ci
```

Current state (Phase 7 close):

| Metric | Threshold (CLAUDE.md) | Actual |
|---|---|---|
| Test count | — | **188** (165 prior + 15 CLI + 7 Gemini provider + 1 from defensive auto-fill split) |
| Coverage | ≥ 85% | **96%+** |
| Ruff violations | 0 | **0** |
| File LOC | ≤ 150 (code lines) | All ≤ 150 |
| Secrets in repo | 0 | `.env` gitignored; only `.env.example` committed |

Test layout: 156 unit tests (one file per module under `tests/unit/`) + 9 integration tests (end-to-end debate, real ChromaDB, multi-round invariants) + 15 CLI tests. Shared fixtures (`fake_provider_factory`, `passthrough_gatekeeper`, `hash_embedder`, ping/score factories) live in `tests/conftest.py`.

---

## Cost analysis

The `ApiGatekeeper` records every LLM call's input/output/cache tokens and computes USD cost per the formula:

$$\text{cost}(m) = \frac{p_\text{in}}{10^6} \cdot t_\text{in} + \frac{p_\text{out}}{10^6} \cdot t_\text{out} + 1.25 \cdot \frac{p_\text{in}}{10^6} \cdot t_\text{cache-write} + 0.10 \cdot \frac{p_\text{in}}{10^6} \cdot t_\text{cache-read}$$

Pricing per model (USD per million tokens, list prices as of submission — verify before final run):

| Provider | Model | Input $/M | Output $/M |
|---|---|---:|---:|
| Google | `gemini-3.1-flash-lite` | 0.10 | 0.40 |
| Google | `gemini-2.5-flash` | 0.30 | 2.50 |
| Google | `gemini-2.5-pro` | 1.25 | 10.00 |
| Anthropic | `claude-haiku-4-5-20251001` | 0.80 | 4.00 |
| Anthropic | `claude-sonnet-4-6` | 3.00 | 15.00 |
| Anthropic | `claude-opus-4-7` | 15.00 | 75.00 |

Default config uses `gemini-3.1-flash-lite` for all three agents (cheapest tier — under $0.10 per 10-round debate at list prices). Swap to `gemini-2.5-flash` / `gemini-2.5-pro` in `config/setup.json.models` if you want stronger reasoning at higher cost. Budget cap = $5.00 (`budget_usd`); the gatekeeper logs a WARNING at 80% and raises `BudgetExceededError` at 100%.

**Optimization strategies in this project:**
1. **Prompt caching** — Anthropic provider marks the system prompt and first messages with `cache_control: { type: "ephemeral" }` (PRD_gatekeeper §9a). Cache reads cost 10% of base input price; the cost report exposes `cache_read_pct`.
2. **Model tiering** — Haiku for the high-frequency debaters, Sonnet only for the Judge. ~5× cheaper than Opus across the whole debate.
3. **Ping word cap** — `max_words_per_ping: 250` in setup.json keeps output tokens bounded per round.

Cost table (Table 4 of the source PDF) will be populated by `notebooks/analysis.ipynb` after the first real debate run. Run the notebook with `uv run jupyter notebook notebooks/analysis.ipynb`.

---

## Sample output

After a debate completes the orchestrator persists `results/debates/debate_<timestamp>.json` containing every ping, every score, the verdict, and the cost report. View it with menu option 5 ("Open a past debate transcript") or load it in the analysis notebook.

Stage 1 manual debate transcript (Phase 1 partner deliverable): see `results/manual_stage1/` once Amr runs the two-CLI session.

---

## Project layout

```text
project-root/
├── README.md                   # this file
├── CLAUDE.md                   # project engineering rules
├── pyproject.toml              # single source of truth for deps
├── uv.lock                     # locked deps, version-controlled
├── justfile                    # task runner: test / lint / cov / run / ingest / ci
├── .env.example                # documents env vars (no real secrets)
├── config/                     # setup.json + rate_limits.json + logging_config.json
├── data/                       # dogs/*.txt + cats/*.txt RAG corpora
├── docs/                       # PRD, PLAN, TODO, PROMPTS, per-mechanism PRDs
├── notebooks/                  # analysis.ipynb (post-run visualizations)
├── skills/                     # one Skill per agent (Lesson 05 §5): dogs/SKILL.md, cats/SKILL.md, judge/SKILL.md
├── src/debate/                 # source — see docs/PLAN.md §10 for module map
└── tests/                      # unit/ + integration/ + conftest.py
```

---

## Lessons learned & reflections

Captured iteratively in [`docs/PROMPTS.md`](docs/PROMPTS.md) — every significant prompt or design decision recorded with context, goal, result, and a lesson. Highlights:

- **Build the API seam before the producer.** `DebateAgent` accepted `RAGLike` / `SearchLike` Protocols in Phase 3.5 (before either implementation existed). Phase 4.4 (web search) and Phase 5 (RAG) dropped in without touching agent code.
- **Inject the clock and the scheduler, not just dependencies.** `Watchdog(clock=FakeClock(), sleep_fn=noop)` made wall-clock-dependent tests instant. Same pattern in the gatekeeper.
- **Mirror prompt-level rules in deterministic code.** The Judge prompt says "ties are forbidden"; `JudgeAgent._tie_break` enforces it independently of what the LLM emits. Defense-in-depth at every contract.
- **The 150-LOC cap is a feature.** Hitting it forced the `gatekeeper.py` / `rate_limiter.py` / `pricing.py` split, which clarified the public/internal boundary that would have stayed implicit otherwise.

---

## Troubleshooting

- **`ImportError: sentence_transformers`** on first ingest — `uv sync` didn't complete. Re-run; the model itself downloads on first `embed_text` call, not on import.
- **`KeyError: 'ANTHROPIC_API_KEY'`** — copy `.env.example` to `.env` and fill in the key. The `python-dotenv` loader reads `.env` automatically when the SDK constructs.
- **ChromaDB `Validation error: name`** — collection names must be 3–512 chars `[a-zA-Z0-9._-]`. The shipped agents use `dogs` / `cats` / test fixtures use `test_col` / `col_a` etc. — only relevant if you write a custom ingest path.
- **Budget alert fires too early** — increase `budget_usd` in `config/setup.json`, or lower the agent models to Haiku in `models.dogs.name` and `models.cats.name`.
- **Coverage below 85%** — should not happen on a clean checkout; if it does, rerun `uv sync` to ensure all test deps are installed.

---

## Contribution guidelines

This is a course-submission repo, so external contributions aren't being accepted. For the project pair:
1. Branch from `main`; never push directly to `main`.
2. Every commit must keep ruff at 0 and tests passing.
3. After every feature: update `docs/TODO.md`, this README's status table, and `docs/PROMPTS.md` if the design decision was non-trivial.
4. PR descriptions should reference the TODO sub-phase they close.

---

## Credits

- **Dr. Yoram Segal** — course instructor, original Exercise 02 spec, submission rubric.
- **Anthropic Claude** (Opus 4.7, 1M-context) — used as the AI pair-programming assistant throughout the implementation. Every prompt iteration with material design impact is logged in `docs/PROMPTS.md`.
- **References:** Toulmin (1958), Aristotle's *Rhetoric*, NSDA Lincoln-Douglas paradigms, IBM Project Debater publications, Irving/Christiano/Amodei (2018) "AI Safety via Debate" (arXiv:1805.00899).

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 Sharbel Maroun and Amr Safadi.
