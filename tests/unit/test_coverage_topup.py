"""Top-up tests for branches missed by earlier modules' unit tests.

These don't belong logically inside the per-module test files — they cover
trivial imports, error branches, and a real daemon-thread roundtrip for the
watchdog. Kept in one place so they're easy to delete later if a refactor
makes them redundant.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest

from debate.services.rag.ingest import main as ingest_main
from debate.services.watchdog import Watchdog, WatchdogConfig
from debate.shared import constants
from debate.shared.config import (
    ConsoleCfg,
    CostLog,
    LoggingConfig,
    Rotation,
)
from debate.shared.logger import (
    FifoRotatingHandler,
    configure_root_logger,
    get_cost_logger,
)


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
    # Hitting start() twice is a no-op.
    wd.start()
    time.sleep(0.05)
    wd.stop()
    assert wd._thread is None  # internal — stop completed


def test_watchdog_loop_logs_and_continues_on_exception() -> None:
    # Force check_once to raise — the _loop must swallow it and keep going.
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


def test_ingest_main_smoke(tmp_path: Path, monkeypatch) -> None:
    """Exercise the CLI entrypoint with a deterministic fake embedder so we
    never load sentence-transformers."""
    import debate.services.rag.ingest as ingest_mod

    class StubEmbedder:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def embed_text(self, t: str) -> list[float]:
            return [0.1] * 8

        def embed_batch(self, ts: list[str]) -> list[list[float]]:
            return [[0.1] * 8 for _ in ts]

    monkeypatch.setattr(ingest_mod, "Embedder", StubEmbedder)
    # Seed the data dir under tmp_path.
    data_root = tmp_path / "data"
    (data_root / "dogs").mkdir(parents=True)
    (data_root / "dogs" / "x.txt").write_text(
        "---\nsource: t\n---\nbody words go here\n", encoding="utf-8"
    )
    # Build a config pointing at the tmp dirs.
    cfg_path = tmp_path / "setup.json"
    repo_setup = Path("config/setup.json").read_text(encoding="utf-8")
    cfg_path.write_text(
        repo_setup.replace(
            '"data/{agent}/chroma"',
            f'"{(tmp_path / "chroma_{agent}").as_posix()}"'.replace("{agent}", "{agent}"),
        ),
        encoding="utf-8",
    )
    rc = ingest_main(
        [
            "--agent",
            "dogs",
            "--config",
            str(cfg_path),
            "--data-root",
            str(data_root),
        ]
    )
    assert rc == 0


def test_ingest_main_rejects_unknown_agent() -> None:
    with pytest.raises(SystemExit):
        ingest_main(["--agent", "fish"])
