"""FIFO-rotating logger. See docs/PLAN.md §3 + config/logging_config.json.

The `FifoRotatingHandler` lives in `_fifo_handler.py`; this file wires it
into the root logger + cost-log sibling per `LoggingConfig`."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from debate.shared._fifo_handler import FifoRotatingHandler
from debate.shared.config import LoggingConfig

__all__ = [
    "FifoRotatingHandler",
    "configure_root_logger",
    "get_cost_logger",
    "get_logger",
    "log_cost_entry",
]


def configure_root_logger(config: LoggingConfig) -> logging.Logger:
    """Attach FIFO + optional console handlers to the `debate` root logger."""
    root = logging.getLogger("debate")
    root.setLevel(config.level)
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    fmt = logging.Formatter(config.format, datefmt=config.datefmt)
    fifo = FifoRotatingHandler(
        config.directory,
        config.rotation.max_files,
        config.rotation.max_lines_per_file,
    )
    fifo.setFormatter(fmt)
    fifo.setLevel(config.level)
    root.addHandler(fifo)
    if config.console.enabled:
        con = logging.StreamHandler()
        con.setLevel(config.console.level)
        con.setFormatter(fmt)
        root.addHandler(con)
    root.propagate = False
    return root


def get_logger(name: str, config: LoggingConfig | None = None) -> logging.Logger:
    """Return a child logger under `debate.<name>`. Pass `config` once at
    process startup to install handlers; later calls without `config`
    just return the named child."""
    if config is not None:
        configure_root_logger(config)
    return logging.getLogger(f"debate.{name}")


def get_cost_logger(config: LoggingConfig) -> logging.Logger:
    """Return a JSONL-only logger for cost entries. Idempotent."""
    logger = logging.getLogger("debate.cost")
    if logger.handlers:
        return logger
    path = Path(config.cost_log.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_cost_entry(logger: logging.Logger, entry: dict) -> None:
    """Serialize a cost entry as one JSONL line."""
    logger.info(json.dumps(entry, separators=(",", ":"), ensure_ascii=False))
