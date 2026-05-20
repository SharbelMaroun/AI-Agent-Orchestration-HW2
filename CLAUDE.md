# Project Guidelines — AI Agent Orchestration HW2

Condensed from `software_submission_guidelines-V3_Summary.md` (Dr. Yoram Segal, v3.00). All rules below are **mandatory** unless marked otherwise.

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
Installation steps · usage (modes/flags/CLI/GUI) · examples & screenshots · configuration guide · contribution guidelines · license & credits.

### `docs/PRD.md`
Project overview, user problem, target audience · measurable goals + KPIs + acceptance criteria · functional & non-functional requirements + user stories · assumptions/dependencies/out-of-scope · timeline & milestones.

### `docs/PLAN.md`
C4 Model diagrams (Context/Container/Component/Code) · UML for complex processes · deployment diagrams · ADRs (rationale, trade-offs, alternatives) · API docs, schemas, contracts.

### `docs/TODO.md`
Tasks with priority + status (Not Started / In Progress / Completed) · phases & milestones · responsibility per task · Definition of Done.

### Per-mechanism PRDs (`docs/PRD_<name>.md`)
For every algorithm, ML model, auth mechanism, search engine, caching, etc. Include theoretical background, I/O spec, performance metrics, constraints, alternatives considered, success criteria, test scenarios.

## 3. Mandatory Workflow
1. Write `docs/PRD.md` → get approval
2. Write `docs/PLAN.md`
3. Write `docs/TODO.md`
4. Write specialized PRDs for each algorithm/mechanism
5. Approve all docs **before** coding
6. Develop while updating `TODO.md`
7. Save results, create visualizations, update `README.md`

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

Document edge cases with input + expected response. Defensive programming, clear error messages, detailed logs, graceful degradation. Generate automated pass/fail reports.

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
