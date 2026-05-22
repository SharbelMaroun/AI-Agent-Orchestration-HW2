# AI-Agent-Orchestration-HW2 — task runner.
# Install just from https://github.com/casey/just then run `just <recipe>`.
# Every command goes through `uv run` per CLAUDE.md §11.

default: lint test

# Install or sync dependencies into the project venv.
sync:
    uv sync

# Run the test suite (coverage gate enforced via pyproject.toml).
test:
    uv run pytest -q

# Run the test suite with the full coverage report.
cov:
    uv run pytest --cov

# Lint with ruff. Zero violations required.
lint:
    uv run ruff check .

# Auto-format with ruff.
format:
    uv run ruff format .

# Verify formatting without modifying files (CI-friendly).
format-check:
    uv run ruff format --check .

# Launch the debate CLI menu.
run:
    uv run python -m debate

# Ingest the dogs corpus into the vector store.
ingest-dogs:
    uv run python -m debate.services.rag.ingest --agent dogs

# Ingest the cats corpus into the vector store.
ingest-cats:
    uv run python -m debate.services.rag.ingest --agent cats

# Ingest both corpora.
ingest: ingest-dogs ingest-cats

# Full pre-submission check: lint, format-check, coverage.
ci: lint format-check cov
