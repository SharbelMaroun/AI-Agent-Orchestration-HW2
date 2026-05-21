"""Shared pytest fixtures. Implementation pending Phase 6.5."""

import pytest


@pytest.fixture
def project_root() -> object:
    """Absolute path to project root (where pyproject.toml lives)."""
    from pathlib import Path

    return Path(__file__).resolve().parent.parent
