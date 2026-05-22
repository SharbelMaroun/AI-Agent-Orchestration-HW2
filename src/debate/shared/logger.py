"""FIFO-rotating logger. See docs/PLAN.md §3 and config/logging_config.json.

Why custom rotation: the assignment requires capped log retention (N files ×
M lines) with FIFO pruning, which stdlib's RotatingFileHandler doesn't model
the same way — it rotates on byte size, not on line count.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

from .config import LoggingConfig

_FILE_PATTERN = re.compile(r"debate-(\d+)\.log$")
_FILE_PREFIX = "debate-"
_FILE_SUFFIX = ".log"
_INDEX_WIDTH = 5


class FifoRotatingHandler(logging.Handler):
    """Logging handler that rotates by line count and keeps at most N files.

    On every Nth line the current file is closed and a new one is opened. When
    the directory holds more than `max_files` rotated files, the oldest is
    deleted (FIFO).
    """

    def __init__(self, directory: str | Path, max_files: int, max_lines_per_file: int) -> None:
        super().__init__()
        if max_files <= 0 or max_lines_per_file <= 0:
            raise ValueError("max_files and max_lines_per_file must be positive")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_files = max_files
        self.max_lines = max_lines_per_file
        self._lock = threading.Lock()
        self._line_count = 0
        self._stream: Any = None
        self._current_path: Path | None = None
        self._open_new_file()

    def _existing_files(self) -> list[Path]:
        files = [p for p in self.directory.iterdir() if _FILE_PATTERN.search(p.name)]
        return sorted(files, key=lambda p: int(_FILE_PATTERN.search(p.name).group(1)))

    def _next_index(self) -> int:
        files = self._existing_files()
        if not files:
            return 1
        last = int(_FILE_PATTERN.search(files[-1].name).group(1))
        return last + 1

    def _open_new_file(self) -> None:
        if self._stream is not None:
            self._stream.close()
        idx = self._next_index()
        self._current_path = self.directory / f"{_FILE_PREFIX}{idx:0{_INDEX_WIDTH}d}{_FILE_SUFFIX}"
        self._stream = self._current_path.open("a", encoding="utf-8")
        self._line_count = 0
        self._prune()

    def _prune(self) -> None:
        files = self._existing_files()
        while len(files) > self.max_files:
            with contextlib.suppress(OSError):
                files[0].unlink()
            files = files[1:]

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            self.handleError(record)
            return
        with self._lock:
            try:
                self._stream.write(msg + "\n")
                self._stream.flush()
                self._line_count += 1
                if self._line_count >= self.max_lines:
                    self._open_new_file()
            except Exception:
                self.handleError(record)

    def close(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.close()
                finally:
                    self._stream = None
        super().close()


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
    """Return a child logger under `debate.<name>`.

    Pass `config` once (usually at process startup) to install handlers; later
    calls without `config` just return the named child.
    """
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
