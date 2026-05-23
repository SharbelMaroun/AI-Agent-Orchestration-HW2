"""Config loader: parses config/*.json + .env. See docs/PLAN.md §7.

Pydantic models live in `_config_models.py`; this file is just the loader
+ version validator. Loaders validate `"version"` at parse time so a stale
binary against a newer config (or vice versa) fails fast.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from debate.shared._config_models import (
    BudgetCfg,
    ConsoleCfg,
    CostLog,
    LoggingConfig,
    ModelPrice,
    ModelRef,
    RagCfg,
    RateLimitConfig,
    Rotation,
    SearchCfg,
    ServiceLimit,
    SetupConfig,
    Timeouts,
    _Cfg,
)

EXPECTED_VERSION = "1.00"

__all__ = [
    "BudgetCfg",
    "ConsoleCfg",
    "CostLog",
    "LoggingConfig",
    "ModelPrice",
    "ModelRef",
    "RagCfg",
    "RateLimitConfig",
    "Rotation",
    "SearchCfg",
    "ServiceLimit",
    "SetupConfig",
    "Timeouts",
    "EXPECTED_VERSION",
    "load_env",
    "load_logging",
    "load_rate_limits",
    "load_setup",
    "validate_version",
]


def _load_json(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_version(cfg: _Cfg, expected: str = EXPECTED_VERSION) -> None:
    """Raise if config version doesn't match the binary's expected version."""
    actual = getattr(cfg, "version", None)
    if actual != expected:
        raise ValueError(f"Config version {actual!r} does not match expected {expected!r}")


def load_setup(path: str | Path = "config/setup.json") -> SetupConfig:
    cfg = SetupConfig.model_validate(_load_json(path))
    validate_version(cfg)
    return cfg


def load_rate_limits(path: str | Path = "config/rate_limits.json") -> RateLimitConfig:
    cfg = RateLimitConfig.model_validate(_load_json(path))
    validate_version(cfg)
    return cfg


def load_logging(path: str | Path = "config/logging_config.json") -> LoggingConfig:
    cfg = LoggingConfig.model_validate(_load_json(path))
    validate_version(cfg)
    return cfg


def load_env(dotenv_path: str | Path = ".env") -> None:
    """Load environment variables from a .env file if present."""
    load_dotenv(dotenv_path=str(dotenv_path), override=False)
