# Project Guidelines — AI Agent Orchestration HW2

Condensed from `software_submission_guidelines-V3_Summary.md` (Dr. Yoram Segal, v3.00). All rules below are **mandatory** unless marked otherwise.

---

## 🚨 NON-NEGOTIABLES — READ FIRST EVERY TURN

These rules are the most common drift points. Before claiming any chunk of work is "done":

1. **Update `docs/TODO.md`** — mark every completed task with `[x]`. Add new tasks discovered during work.
2. **Update `README.md`** — both the user-manual sections AND the homework-report sections. Stale README = lost points.
3. **Update `docs/PROMPTS.md`** — log every significant prompt iteration or design decision with date, context, goal, result, lesson.
4. **No file > 150 LOC** (code files only; excludes blank + comment lines).
5. **No hardcoded values** — everything in `config/` or env vars. See §8.
6. **No secrets in repo** — only `.env.example`, never `.env`. See §9.
7. **Tests ≥ 85% coverage** (`pytest --cov fail_under = 85`). See §6.
8. **Ruff = 0 violations** (`ruff check`). See §7.
9. **All API calls through Gatekeeper** — no direct LLM/search/embedding call outside it. See §5.
10. **`uv` only** — never `pip`, `venv`, `virtualenv`, `python -m pip`. See §11.

**Failure mode to watch for:** finishing a chunk of code without updating TODO + README + PROMPTS. After every `Write` or `Edit` to code/config, ask: *"Which of these three docs changed because of this edit?"*

---

## Homework-specific spec (auto-loaded each session)

Follow the project spec in @docs/PRD.md and architecture in @docs/PLAN.md.
Per-mechanism details: @docs/PRD_judge.md, @docs/PRD_dogs.md, @docs/PRD_cats.md, @docs/PRD_gatekeeper.md, @docs/PRD_rag.md, @docs/PRD_watchdog.md.

---

## 1. Mandatory Project Structure

```text
project-root/
├── README.md                   # MANDATORY — user manual (see §2)
├── pyproject.toml              # Single source of truth for deps
├── uv.lock                     # Locked deps, version-controlled
├── .env-example                # Dummy secret placeholders
├── .gitignore                  # Must ignore .env, *.key, *.pem, credentials.json
├── docs/                       # MANDATORY
│   ├── PRD.md                  # Product Requirements
│   ├── PLAN.md                 # Architecture & Design
│   ├── TODO.md                 # Task tracking
│   ├── PROMPTS.md              # Prompt engineering log (see §17)
│   └── PRD_<mechanism>.md      # One per algorithm/central mechanism
├── config/
│   ├── setup.json              # Main config (with "version" key, start 1.00)
│   ├── rate_limits.json        # Rate limits (with "version" key)
│   └── logging_config.json
├── src/<package>/
│   ├── __init__.py             # Exports public API via __all__, defines __version__
│   ├── sdk/sdk.py              # SDK layer — single entry point
│   ├── services/               # Business logic
│   ├── shared/
│   │   ├── gatekeeper.py       # Centralized API gatekeeper
│   │   ├── config.py
│   │   ├── version.py          # Code version, start 1.00
│   │   └── constants.py
│   └── main.py
├── tests/
│   ├── unit/                   # Mirror src/ structure
│   ├── integration/
│   └── conftest.py             # Shared fixtures
├── data/                       # Input data
├── results/                    # Experiment results
├── assets/                     # Images, graphs
└── notebooks/                  # Analysis notebooks
```

## 2. Required Documents

### `README.md` must include
`README.md` is **both the user manual and the homework report**. It must contain:

**User manual section:**
- Installation steps · usage (modes/flags/CLI/GUI) · configuration guide · contribution guidelines · license & credits.

**Homework report section:**
- **Authors:** both partners' full names + GitHub handles + emails clearly displayed at the top of the report. For this project: Sharbel Maroun (@SharbelMaroun) and Amr Safadi.
- **Submitted to:** Dr. Yoram Segal, course name, date.
- Project summary and goals (what we built and why).
- Architecture overview with diagram (link to or embed from `docs/PLAN.md`).
- Key design decisions (link to ADRs).
- Stage 1 deliverable — manual debate transcript with screenshots.
- Sample end-to-end run output — full debate transcript + judge verdict.
- Cost analysis table (Table 4 from §11 of the source PDF): tokens per model + dollar cost.
- Optimization strategies used (caching, model choice, ping limits).
- Lessons learned and reflections from prompt engineering.
- Screenshots of every screen/state (terminal menu, mid-debate, verdict, cost report).
- Known limitations and out-of-scope items.
- Troubleshooting section.

**Update rule:** `README.md` must be kept current as work progresses — just like `docs/TODO.md`. Every time a new feature lands, a new screenshot is captured, a new debate is run, or a design decision shifts, `README.md` must be updated in the same commit. Stale README = failed grading on "documentation freshness."

### `docs/PRD.md`
Project overview, user problem, target audience · measurable goals + KPIs + acceptance criteria · functional & non-functional requirements + user stories · assumptions/dependencies/out-of-scope · timeline & milestones.

### `docs/PLAN.md`
C4 Model diagrams (Context/Container/Component/Code) · UML for complex processes · deployment diagrams · ADRs (rationale, trade-offs, alternatives) · API docs, schemas, contracts.

### `docs/TODO.md`
Tasks with priority + status (Not Started / In Progress / Completed) · phases & milestones · responsibility per task · Definition of Done.
**Granularity: 500–700 tasks total.** Each task must be small and atomic (one concrete deliverable — a single file, function, test, config entry, doc section, or screenshot). Break large work into many fine-grained tasks rather than a few coarse ones.

### Per-mechanism PRDs (`docs/PRD_<name>.md`)
For every algorithm, ML model, auth mechanism, search engine, caching, etc. Include theoretical background, I/O spec, performance metrics, constraints, alternatives considered, success criteria, test scenarios.

## 3. Mandatory Workflow
1. Write `docs/PRD.md` → get approval
2. Write `docs/PLAN.md`
3. Write `docs/TODO.md`
4. Write specialized PRDs for each algorithm/mechanism
5. Approve all docs **before** coding
6. Develop while updating `TODO.md` **and `README.md`** every commit (mark tasks complete; add/update report sections as features land).
7. Save results, create visualizations, capture screenshots, and update `README.md` (both the user manual AND the homework report sections).
8. Keep `docs/PROMPTS.md` updated with every significant prompt iteration.

## 4. Code Rules

- **Max 150 lines per file** (excludes blank/comment lines). If exceeded → split (extract helpers, mixins, 50/50 split, constants, models). **Never compress** to fit.
- **SDK is the sole entry point** for all business logic. GUI/CLI/REST/third-party may only import the SDK. No business logic in GUI/CLI layers.
- **OOP, no duplication:**
  - Same function body in 2+ files → extract to shared module
  - Same `try/except` in 3+ files → wrapper function
  - Same method in 3+ classes → base class or mixin
  - Variations → Template Method pattern
- **Mixin rules:** one concern each · no method overrides between mixins · independently testable.
- **Comments:** explain *why*, not *what*. Docstrings on every function/module. Update comments alongside code.
- **Naming:** descriptive, single-responsibility functions, DRY, consistent style.
- **Imports:** relative paths or package names only — no absolute paths. File I/O also relative to package.

## 5. API Gatekeeper (Mandatory)

All external API calls route through a centralized `ApiGatekeeper`. No service makes direct API calls.

**Interface:**
```python
class ApiGatekeeper:
    def __init__(self, config: RateLimitConfig): ...
    def execute(self, api_call, *args, **kwargs):
        # Check rate limits → queue if reached → retry transient failures → log all
        ...
    def get_queue_status(self) -> QueueStatus: ...
```

**Rate limits** read from `config/rate_limits.json` (never hardcoded):
```json
{
  "rate_limits": {
    "version": "1.00",
    "services": {
      "default": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3
      }
    }
  }
}
```

**Queue:** FIFO · max depth in config · backpressure alert when full · drain when limit resets. Overflow is **queued, never rejected**.

## 6. Testing (TDD)

- **Red → Green → Refactor.** Tests written before/with code, never after.
- Every module → corresponding test file (mirror `src/` in `tests/unit/`).
- Every public function → at least one test (happy path + error cases).
- Mock all external deps (DB, files, APIs). No test depends on external services.
- Test files ≤ 150 lines.
- **Coverage ≥ 85%** (statement, branch, path for critical paths). Suite must fail below threshold.

```toml
[tool.coverage.run]
source = ["src"]
omit = ["src/main.py", "*/tests/*", "src/**/gui/*"]

[tool.coverage.report]
fail_under = 85
```

Document edge cases with input + expected response. Defensive programming, clear error messages, detailed logs, graceful degradation. Generate automated pass/fail reports. **Capture screenshots of faults** (CLI tracebacks, GUI error states, browser console) when they meaningfully illustrate failure modes; embed in README or `assets/`.

## 7. Linting — Zero Ruff Violations

`ruff check` must pass with **0 errors**.

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E","F","W","I","N","UP","B","C4","SIM"]
ignore = ["E501"]
```

## 8. No Hardcoded Values

| Category | ❌ Wrong | ✅ Correct |
|---|---|---|
| API URLs | `"https://api.example.com"` | `cfg.get("api_url")` |
| Rate limits | `rate_limit = 10` | `cfg.get("rate_limit", 10)` |
| Timeouts | `timeout=60` | `cfg.get("timeout", 60)` |
| Secrets | `api_key = "abc123"` | `os.environ.get("API_KEY")` |

**Allowed in code:** physical/math constants, default param values, `constants.py`, `Enum` values.

## 9. Security & Secrets

- **Never** store keys/passwords/tokens in source code.
- Use `os.environ.get("...")` only.
- `.gitignore` must include: `.env`, `credentials.json`, `*.key`, `*.pem`.
- `.env-example` with dummy values is **mandatory** when pushing to GitHub.
- Rotate keys, monitor usage, least-privilege permissions.

## 10. Versioning

| Item | Location | Initial |
|---|---|---|
| Code version | `src/<pkg>/shared/version.py` | 1.00 |
| Config version | `"version"` key in JSON | 1.00 |
| Rate limit version | `rate_limits.version` | 1.00 |

App must validate config version at runtime.

## 11. `uv` Package Manager — Mandatory

**Forbidden:** `pip`, `virtualenv`, `venv`, `python -m pip install`, `requirements.txt`.

| Task | ✅ uv | ❌ Forbidden |
|---|---|---|
| Install deps | `uv sync` | `pip install` |
| Add dep | `uv add <pkg>` | `pip install <pkg>` |
| Run script | `uv run python script.py` | `python script.py` |
| Run tests | `uv run pytest tests/` | `python -m pytest` |
| Lock | `uv lock` | `pip freeze` |

`pyproject.toml` is single source of truth. `uv.lock` is committed. All tools run via `uv run`.

## 12. Research & Visualization

- **Parameter research:** systematic experiments, controlled changes, sensitivity analysis (partial derivatives / variance-based / OAT).
- **Analysis notebook:** Jupyter or similar · LaTeX for equations · academic references · compare algorithms/configs.
- **Visualizations:** bar (comparisons) · line (trends) · scatter (correlations) · heatmap (sensitivity) · box (distributions) · waterfall (variance). Clear labels, accessible colors, legends, high resolution.

## 13. UI/UX

- **Usability:** learnability, efficiency, memorability, error prevention, satisfaction.
- **Nielsen's 10 heuristics** apply.
- Document every screen + state with screenshots, user workflows, interactions, accessibility notes.

## 14. Costs & Pricing

Track input/output tokens per model. Compute cost per million tokens. Forecast budget, monitor real-time, alert on overruns. Optimize via token reduction, batch processing, model selection.

## 15. Parallel Processing

- **Multiprocessing** for CPU-bound (math, image, training).
- **Multithreading** for I/O-bound (network, DB, files).
- **Thread safety:** locks for shared state · `queue.Queue` for data transfer · avoid deadlocks · context managers · prevent race conditions.

## 16. Building Block Design

Every component is an independent unit with: **Input** (types, range, validation) · **Output** (types, format, edge behavior) · **Setup** (defaults, configuration). Principles: Single Responsibility · Separation of Concerns · Reusability · Testability (via dependency injection).

## 17. Prompt Engineering Log (`docs/PROMPTS.md`)

Mandatory deliverable. Log every significant prompt used to build the project, with: context, goal, example outputs, refinements made, and recommended practices learned. Listed in the final submission checklist as "documented prompt book."

## 18. ISO/IEC 25010 Quality

Functional Suitability · Performance Efficiency · Compatibility · Usability · Reliability · Security · Maintainability · Portability.

## 19. Expansion & Maintainability

- **Plugin architecture:** new functionality plugs in via clear extension interfaces; do not modify core code to add features.
- **Lifecycle hooks:** support connection points such as `beforeCreate` / `afterUpdate` (or equivalents) so consumers can extend behavior without forking.
- **Middleware:** support a middleware chain for cross-cutting concerns (logging, auth, rate-limit decoration).
- **API-first design:** every component exposes a stable public API before any consumer is built on top of it.
- **Maintainable code:** modular · separated concerns · reusable components · testable · easy to debug.

## 20. Package Organization

- **`pyproject.toml`** (preferred) specifies name, version, description, author, license, dependencies (pinned).
- **`__init__.py` is mandatory** in the package root **AND every sub-directory**. Use it to export the public API via `__all__` and to define `__version__`.
- **Relative imports or package names only.** Never filesystem-absolute paths. File I/O is also relative to the package.
- **Package checklist (verify before commit):**
  1. `pyproject.toml` exists with name, version, pinned dependencies.
  2. `__init__.py` in root + every sub-dir; exports public API via `__all__`; defines `__version__`.
  3. Source under `src/<pkg>/`, tests under `tests/`, docs under `docs/`.
  4. All imports relative; no absolute paths anywhere.

## 21. Git Workflow

- **Commits:** meaningful messages, conventional style (e.g., `feat:`, `fix:`, `docs:`, `refactor:`).
- **Branches:** feature branches off `main`; never push directly to `main`.
- **Pull Requests:** every merge to `main` goes via PR with code review; PR description references the TODO sub-phase it closes.
- **Tags:** tag major versions (`v1.0.0`, …) on the merge commit.
- **History:** linear and clean; squash or rebase trivial fix-ups before merging.

## 22. Final Submission Checklist

Before submission, verify every box. Maps to source §17 + §20.9.

**Documentation**
- [ ] `README.md` complete: install, usage, examples, screenshots, troubleshooting, license, credits, authors, homework-report sections.
- [ ] `docs/PRD.md`, `docs/PLAN.md`, `docs/TODO.md` current and consistent with code.
- [ ] One `docs/PRD_<mechanism>.md` per algorithm/central mechanism.
- [ ] `docs/PROMPTS.md` ("prompt book") logs every significant prompt with context, goal, result, lesson.

**Architecture & code**
- [ ] All business logic routed through the SDK.
- [ ] All external API calls routed through `ApiGatekeeper`.
- [ ] No code duplication (extracted at 2+ copies); mixins follow single-concern rule.
- [ ] Every file ≤ 150 LOC (excluding blanks + comments).
- [ ] Comments explain *why*; docstrings on every public function/class/module.
- [ ] Consistent style, descriptive names.

**Testing & quality**
- [ ] TDD: tests written before/with the code.
- [ ] `uv run pytest --cov` ≥ 85%, 0 failures.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` both 0 violations.
- [ ] Edge cases documented with input + expected response.
- [ ] Automated pass/fail reports generated.

**Configuration & security**
- [ ] All config in `config/*.json`, versioned (`"version": "1.00"`).
- [ ] No hardcoded values in source.
- [ ] `.env` git-ignored; only `.env-example` (or `.env.example`) committed.
- [ ] No API keys / passwords / tokens anywhere in git history.
- [ ] `.gitignore` covers `.env`, `*.key`, `*.pem`, `credentials.json`.
- [ ] `pyproject.toml` + `uv.lock` committed; `uv` is the only package manager used.

**Research & visualization**
- [ ] Systematic experiments with controlled parameter variations.
- [ ] Sensitivity analysis present.
- [ ] Analysis notebook with high-quality graphs (LaTeX equations, academic refs where relevant).
- [ ] Token-cost table + optimization strategies documented in README.

**Scalability & standards**
- [ ] Extension points documented (plugin interfaces, hooks, middleware).
- [ ] Package layout matches §20 (incl. `__init__.py` in every sub-dir).
- [ ] Parallel-processing sections (if any) are thread-safe.
- [ ] Building-block design (Input / Output / Setup) for every component.
- [ ] ISO/IEC 25010 attributes considered.

**General**
- [ ] Clean git history; meaningful commit messages; tagged release.
- [ ] LICENSE file present; attributions complete.
- [ ] Public GitHub repo (or shared with lecturer); both partners link the same URL on Moodle.

---

## Quick Reference

| Rule | Threshold |
|---|---|
| File size | ≤ 150 lines |
| Test coverage | ≥ 85% |
| Ruff violations | 0 |
| Hardcoded values | 0 in source |
| All API calls | Via gatekeeper |
| All business logic | Via SDK |
| Package manager | `uv` only |
| Secrets in code | 0 (use env vars + `.env-example`) |
| Version start | 1.00 |
| OOP duplication | Extract at 2+ copies |
| `__init__.py` | In root + every sub-dir; exports `__all__` + `__version__` |
| Imports | Relative or package-name only — never filesystem-absolute paths |
| Git workflow | Feature branch → PR → review → merge; tag releases |
| Extension points | Plugin interfaces + lifecycle hooks + middleware |
| Final checklist | §22 — verify before every submission |
