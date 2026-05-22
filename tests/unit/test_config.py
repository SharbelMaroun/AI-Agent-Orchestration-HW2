"""Config loader tests (Phase 3.2)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from debate.shared.config import (
    load_logging,
    load_rate_limits,
    load_setup,
    validate_version,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CFG_DIR = REPO_ROOT / "config"


def test_config_loads_setup():
    cfg = load_setup(CFG_DIR / "setup.json")
    assert cfg.version == "1.00"
    assert cfg.num_rounds >= 1
    assert {"dogs", "cats", "judge"}.issubset(cfg.models.keys())
    assert cfg.models["dogs"].provider in {"anthropic", "google", "openai"}


def test_config_loads_rate_limits():
    cfg = load_rate_limits(CFG_DIR / "rate_limits.json")
    assert cfg.version == "1.00"
    assert "default" in cfg.services
    assert cfg.services["default"].max_retries >= 0
    assert 0 <= cfg.budget.warning_threshold_pct <= 100


def test_config_loads_logging():
    cfg = load_logging(CFG_DIR / "logging_config.json")
    assert cfg.version == "1.00"
    assert cfg.rotation.max_files > 0
    assert cfg.cost_log.format == "jsonl"


def test_config_rejects_wrong_version(tmp_path: Path):
    data = json.loads((CFG_DIR / "setup.json").read_text(encoding="utf-8"))
    data["version"] = "9.99"
    p = tmp_path / "setup.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        load_setup(p)


def test_config_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_setup(tmp_path / "does_not_exist.json")


def test_config_rejects_extra_field(tmp_path: Path):
    """extra='forbid' guards against typos drifting silently."""
    data = json.loads((CFG_DIR / "setup.json").read_text(encoding="utf-8"))
    data["rogue_field"] = True
    p = tmp_path / "setup.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_setup(p)


def test_validate_version_helper_passes():
    cfg = load_setup(CFG_DIR / "setup.json")
    validate_version(cfg, expected="1.00")  # does not raise


def test_validate_version_helper_rejects():
    cfg = load_setup(CFG_DIR / "setup.json")
    with pytest.raises(ValueError):
        validate_version(cfg, expected="2.00")
