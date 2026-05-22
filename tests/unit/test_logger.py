"""Unit tests for debate.shared.logger."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pytest

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
    get_logger,
    log_cost_entry,
)

ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _make_config(tmp_path: Path, max_files: int = 3, max_lines: int = 2) -> LoggingConfig:
    return LoggingConfig(
        version="1.00",
        level="DEBUG",
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        directory=str(tmp_path / "logs"),
        rotation=Rotation(max_files=max_files, max_lines_per_file=max_lines),
        cost_log=CostLog(path=str(tmp_path / "cost.jsonl"), format="jsonl"),
        console=ConsoleCfg(enabled=False, level="INFO"),
    )


@pytest.fixture(autouse=True)
def _reset_loggers():
    """Detach handlers from `debate.*` loggers between tests."""
    yield
    for name in ("debate", "debate.cost"):
        lg = logging.getLogger(name)
        for h in list(lg.handlers):
            lg.removeHandler(h)
            h.close()


def test_handler_rotates_at_max_lines(tmp_path: Path) -> None:
    h = FifoRotatingHandler(tmp_path, max_files=10, max_lines_per_file=2)
    h.setFormatter(logging.Formatter("%(message)s"))
    for i in range(5):
        rec = logging.LogRecord("t", logging.INFO, __file__, i, f"line-{i}", None, None)
        h.emit(rec)
    h.close()
    files = sorted(tmp_path.glob("debate-*.log"))
    assert len(files) == 3  # 2 + 2 + 1
    assert files[0].read_text(encoding="utf-8").splitlines() == ["line-0", "line-1"]
    assert files[-1].read_text(encoding="utf-8").splitlines() == ["line-4"]


def test_handler_prunes_oldest_when_over_max_files(tmp_path: Path) -> None:
    h = FifoRotatingHandler(tmp_path, max_files=2, max_lines_per_file=1)
    h.setFormatter(logging.Formatter("%(message)s"))
    for i in range(5):
        rec = logging.LogRecord("t", logging.INFO, __file__, i, f"line-{i}", None, None)
        h.emit(rec)
    h.close()
    files = sorted(tmp_path.glob("debate-*.log"))
    assert len(files) <= 2
    contents = [f.read_text(encoding="utf-8").strip() for f in files]
    assert "line-0" not in contents  # oldest pruned


def test_handler_rejects_invalid_params(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FifoRotatingHandler(tmp_path, max_files=0, max_lines_per_file=1)
    with pytest.raises(ValueError):
        FifoRotatingHandler(tmp_path, max_files=1, max_lines_per_file=0)


def test_configure_root_logger_writes_iso_timestamp(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    root = configure_root_logger(cfg)
    root.info("hello")
    for h in root.handlers:
        h.flush()
    files = list(Path(cfg.directory).glob("debate-*.log"))
    assert files
    line = files[0].read_text(encoding="utf-8").splitlines()[0]
    assert ISO_TS.match(line)
    assert "hello" in line


def test_get_logger_returns_child(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    lg = get_logger("orchestrator", cfg)
    assert lg.name == "debate.orchestrator"
    assert lg.parent.name == "debate"


def test_logger_respects_level_from_config(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    cfg = cfg.model_copy(update={"level": "WARNING"})
    root = configure_root_logger(cfg)
    root.debug("debug-msg")
    root.warning("warn-msg")
    for h in root.handlers:
        h.flush()
    body = "\n".join(p.read_text(encoding="utf-8") for p in Path(cfg.directory).glob("*.log"))
    assert "warn-msg" in body
    assert "debug-msg" not in body


def test_cost_logger_writes_jsonl(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    cost = get_cost_logger(cfg)
    log_cost_entry(cost, {"model": "claude-opus", "tokens_in": 10, "tokens_out": 5})
    for h in cost.handlers:
        h.flush()
    line = Path(cfg.cost_log.path).read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["model"] == "claude-opus"
    assert parsed["tokens_in"] == 10


def test_cost_logger_is_idempotent(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    a = get_cost_logger(cfg)
    b = get_cost_logger(cfg)
    assert a is b
    assert len(a.handlers) == 1
