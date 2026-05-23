"""Pydantic models mirroring the JSON config files. Extracted from
`config.py` so the loader module stays compact."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRef(_Cfg):
    provider: str
    name: str


class Timeouts(_Cfg):
    agent_response_seconds: int = Field(gt=0)
    watchdog_heartbeat_seconds: int = Field(gt=0)
    watchdog_kill_after_seconds: int = Field(gt=0)
    max_restarts_per_agent: int = Field(ge=0)


class RagCfg(_Cfg):
    enabled: bool
    k: int = Field(gt=0)
    chunk_size: int = Field(gt=0)
    embedder: str
    persist_dir: str


class SearchCfg(_Cfg):
    provider: str
    max_results: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)


class ModelPrice(_Cfg):
    input_per_million_usd: float = Field(ge=0)
    output_per_million_usd: float = Field(ge=0)


class SetupConfig(_Cfg):
    """Mirrors `config/setup.json`."""

    version: str
    topic: str
    num_rounds: int = Field(gt=0)
    max_words_per_ping: int = Field(gt=0)
    budget_usd: float = Field(ge=0)
    models: dict[str, ModelRef]
    timeouts: Timeouts
    rag: RagCfg
    search: SearchCfg
    pricing: dict[str, dict[str, ModelPrice]]


class ServiceLimit(_Cfg):
    requests_per_minute: int = Field(gt=0)
    requests_per_hour: int = Field(gt=0)
    concurrent_max: int = Field(gt=0)
    retry_after_seconds: int = Field(ge=0)
    max_retries: int = Field(ge=0)
    queue_max_depth: int = Field(gt=0)
    retryable_status_codes: list[int]


class BudgetCfg(_Cfg):
    warning_threshold_pct: int = Field(ge=0, le=100)
    hard_limit_pct: int = Field(ge=0, le=100)


class RateLimitConfig(_Cfg):
    """Mirrors `config/rate_limits.json`."""

    version: str
    services: dict[str, ServiceLimit]
    budget: BudgetCfg


class Rotation(_Cfg):
    max_files: int = Field(gt=0)
    max_lines_per_file: int = Field(gt=0)


class CostLog(_Cfg):
    path: str
    format: str


class ConsoleCfg(_Cfg):
    enabled: bool
    level: str


class LoggingConfig(_Cfg):
    """Mirrors `config/logging_config.json`."""

    version: str
    level: str
    format: str
    datefmt: str
    directory: str
    rotation: Rotation
    cost_log: CostLog
    console: ConsoleCfg
