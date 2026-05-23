"""Top-up tests for branches missed by per-module unit tests.

Watchdog-thread + logger console branches stay here; ingest CLI edge cases
live in `test_ingest_cli.py` (split for the 150-LOC test cap, CLAUDE.md §6).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from debate.services.watchdog import Watchdog, WatchdogConfig
from debate.shared import constants
from debate.shared.config import ConsoleCfg, CostLog, LoggingConfig, Rotation
from debate.shared.logger import FifoRotatingHandler, configure_root_logger, get_cost_logger


def test_constants_module_is_importable() -> None:
    assert constants.SIDE_DOGS == "dogs"
    assert constants.SIDE_CATS == "cats"
    assert constants.DEFAULT_MAX_TOKENS > 0
    assert constants.MessageType.OPENING_BRIEF.value == "OPENING_BRIEF"
    assert constants.DEFAULT_CONFIG_DIR.name == "config"


def _logging_cfg(tmp_path: Path, console: bool = False) -> LoggingConfig:
    return LoggingConfig(
        version="1.00",
        level="INFO",
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        directory=str(tmp_path / "logs"),
        rotation=Rotation(max_files=2, max_lines_per_file=2),
        cost_log=CostLog(path=str(tmp_path / "c.jsonl"), format="jsonl"),
        console=ConsoleCfg(enabled=console, level="INFO"),
    )


def test_logger_with_console_enabled_adds_stream_handler(tmp_path: Path) -> None:
    cfg = _logging_cfg(tmp_path, console=True)
    root = configure_root_logger(cfg)
    stream_handlers = [
        h
        for h in root.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, FifoRotatingHandler)
    ]
    assert len(stream_handlers) == 1
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()


def test_get_cost_logger_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "deeply" / "nested" / "cost.jsonl"
    cfg = LoggingConfig(
        version="1.00",
        level="INFO",
        format="%(message)s",
        datefmt="%H:%M:%S",
        directory=str(tmp_path / "logs"),
        rotation=Rotation(max_files=2, max_lines_per_file=2),
        cost_log=CostLog(path=str(nested), format="jsonl"),
        console=ConsoleCfg(enabled=False, level="INFO"),
    )
    lg = get_cost_logger(cfg)
    lg.info('{"x":1}')
    for h in lg.handlers:
        h.flush()
    assert nested.exists()
    for h in list(lg.handlers):
        lg.removeHandler(h)
        h.close()


class _Proc:
    def __init__(self) -> None:
        self._alive = True

    def terminate(self) -> None:
        self._alive = False

    def kill(self) -> None:
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive


def test_watchdog_start_stop_real_thread() -> None:
    cfg = WatchdogConfig(
        heartbeat_seconds=0.05,
        kill_after_seconds=10.0,
        max_restarts_per_agent=1,
        terminate_grace_seconds=0.0,
        poll_interval_seconds=0.01,
    )
    wd = Watchdog(cfg, logger=logging.getLogger("test"))
    wd.register("dogs", _Proc(), lambda: _Proc())
    wd.start()
    wd.start()  # double-start is a no-op
    time.sleep(0.05)
    wd.stop()
    assert wd._thread is None


def test_watchdog_loop_logs_and_continues_on_exception() -> None:
    """Force check_once to raise — the _loop must swallow it and keep going."""
    cfg = WatchdogConfig(
        heartbeat_seconds=0.05,
        kill_after_seconds=10.0,
        max_restarts_per_agent=1,
        terminate_grace_seconds=0.0,
        poll_interval_seconds=0.01,
    )
    wd = Watchdog(cfg, logger=logging.getLogger("test"))
    iteration = {"n": 0}
    real_check = wd.check_once

    def flaky_check() -> None:
        iteration["n"] += 1
        if iteration["n"] == 1:
            raise RuntimeError("oops")
        real_check()

    wd.check_once = flaky_check  # type: ignore[assignment]
    wd.start()
    deadline = time.monotonic() + 0.5
    while iteration["n"] < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    wd.stop()
    assert iteration["n"] >= 2
