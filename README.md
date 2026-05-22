# AI Agent Orchestration HW2 — Dogs vs Cats Debate

> ⚠️ **This README is a work-in-progress report.** Sections are filled in as phases complete. The full report (Phase 7.2 of `docs/TODO.md`) will land with screenshots, transcripts, and cost analysis once implementation is done.

## Authors

- **Sharbel Maroun** ([@SharbelMaroun](https://github.com/SharbelMaroun)) — `142183717+SharbelMaroun@users.noreply.github.com`
- **Amr Safadi** — `safadiamr02@gmail.com`

## Submission

- **Course:** Orchestration of AI Agents
- **Instructor:** Dr. Yoram Segal
- **Assignment:** Exercise 02 — AI Agent Debate
- **Topic:** Are dogs or cats the better pet? (judged on persuasion, not facts)

## Project summary

Three AI agents conduct a structured debate under Python orchestration:

| Agent | Role | Style |
|---|---|---|
| **Dogs agent** | Argues dogs are the better pet | logos + ethos (cites studies, authority) |
| **Cats agent** | Argues cats are the better pet | pathos + Socratic (vivid imagery, reframing) |
| **Judge** | Scores every ping, declares a non-tie winner | neutral, 5-dimension rubric |

The Judge moderates all communication (no direct Pro ↔ Con). Each agent maintains its own conversation history and uses a web-search tool plus a private RAG corpus. The system runs as 3 OS processes communicating via JSON over `multiprocessing.Queue`. Token usage and dollar cost are tracked through a centralized Gatekeeper; a Watchdog restarts any hung agent.

## Status

| Phase | Description | Status |
|---|---|---|
| 0 | Documentation & design | 🟨 In progress (review pending) |
| 1 | Manual debate (Stage 1 transcript) | ⬜ Not started |
| 2 | Project bootstrap | ✅ Complete |
| 3 | Core code (schemas, providers, agents, orchestrator, SDK) | ✅ Complete — all 10 sub-phases (schemas, config, providers, BaseAgent, DebateAgent, DogsAgent, CatsAgent, JudgeAgent, Orchestrator, SDK) |
| 4 | Engineering (gatekeeper, watchdog, logger, search) | 🟨 In progress — 4.3 logger ✅ (FIFO rotation + JSONL cost log); 4.1 gatekeeper next |
| 5 | RAG | ⬜ Not started |
| 6 | Tests + coverage ≥ 85% | ⬜ Not started |
| 7 | Polish (CLI menu, README full report, notebook) | ⬜ Not started |
| 8 | Submission | ⬜ Not started |

See `docs/TODO.md` for the full ~560-task breakdown.

**Current test snapshot (2026-05-22, Phase 3 + 4.3 complete):** 93 unit tests pass · ruff 0 violations · every file ≤ 150 LOC · `DebateSDK().run_debate()` produces a full `DebateResult` end-to-end with mocked LLMs · FIFO-rotating logger + JSONL cost log online. Coverage gate stays deferred to Phase 6 per `docs/PROMPTS.md` until the remaining Phase 4 services (gatekeeper, watchdog, web search) and Phase 5 (RAG) come online.

**Deferred from Phase 3.9 (tracked in `docs/TODO.md`):** the Orchestrator runs synchronously; `multiprocessing.Process` wrapping and SIGINT/SIGTERM handling land alongside the Watchdog in Phase 4.

## Quick links

- [Product Requirements (PRD)](docs/PRD.md)
- [Architecture & Plan](docs/PLAN.md)
- [Per-mechanism PRDs](docs/) — judge, dogs, cats, gatekeeper, rag, watchdog
- [Task list](docs/TODO.md)
- [Prompt engineering log](docs/PROMPTS.md)
- [Project guidelines](CLAUDE.md)

## Installation (preview)

```powershell
# 1. Install dependencies
uv sync

# 2. Set up secrets
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY=sk-ant-...

# 3. Run (not yet functional — Phase 7.1)
uv run python -m debate
```

## Tech stack

- **Python** ≥ 3.10 (developed on 3.13)
- **Package manager:** `uv`
- **LLM:** Anthropic Claude (provider-agnostic — swap via config)
- **Vector store:** ChromaDB (local persistent)
- **Embeddings:** sentence-transformers (local, free)
- **Web search:** DuckDuckGo
- **Testing:** pytest + pytest-cov (≥ 85% required)
- **Lint:** ruff (0 violations required)

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 Sharbel Maroun and Amr Safadi.
