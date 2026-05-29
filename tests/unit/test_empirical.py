"""Unit tests for empirical analysis (debate.services.analysis.empirical)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from debate.services.analysis.empirical import (
    _distribution,
    empirical_summary,
    load_results,
)
from debate.shared.schemas import DebateResult, Ping, Score, Verdict

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


def _write_debate(dirpath: Path, name: str, *, winner: str, margin: int, clash: int) -> None:
    ping = Ping(round=1, side="dogs", text="t", timestamp=NOW, tokens_in=100, tokens_out=50)
    score = Score(
        ping_round=1,
        side="dogs",
        structure=3,
        logos=2,
        pathos=2,
        ethos=2,
        clash=clash,
        rationale="r",
    )
    result = DebateResult(
        topic="cats vs dogs",
        pings=[ping],
        scores=[score],
        verdict=Verdict(
            winner=winner,
            dogs_total=140,
            cats_total=140 - margin,
            margin=margin,
            written_rationale="x",
        ),
        cost_report={
            "total_usd": 0.05,
            "by_model": {"openai/gpt-4o-mini": {"input_tokens": 100, "output_tokens": 50}},
        },
        started_at=NOW,
        finished_at=NOW,
    )
    (dirpath / name).write_text(result.model_dump_json(), encoding="utf-8")


def test_load_results_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert load_results(tmp_path / "nope") == []


def test_empirical_summary_empty(tmp_path: Path) -> None:
    stats = empirical_summary(tmp_path)
    assert stats.n_debates == 0
    assert stats.dogs_win_rate == 0.0
    assert stats.metrics == {}


def test_empirical_summary_aggregates(tmp_path: Path) -> None:
    _write_debate(tmp_path, "debate_001.json", winner="dogs", margin=8, clash=3)
    _write_debate(tmp_path, "debate_002.json", winner="cats", margin=4, clash=1)
    stats = empirical_summary(tmp_path)
    assert stats.n_debates == 2
    assert stats.dogs_win_rate == 0.5
    assert stats.metrics["margin"].mean == 6.0
    assert stats.dimensions["clash"].minimum == 1.0
    assert stats.dimensions["clash"].maximum == 3.0


def test_empirical_summary_total_tokens(tmp_path: Path) -> None:
    _write_debate(tmp_path, "debate_001.json", winner="dogs", margin=8, clash=3)
    stats = empirical_summary(tmp_path)
    assert stats.metrics["total_tokens"].mean == 150.0  # 100 in + 50 out


def test_distribution_empty_is_zero() -> None:
    d = _distribution("x", [])
    assert d.n == 0 and d.mean == 0.0 and d.median == 0.0


def test_distribution_single_value() -> None:
    d = _distribution("x", [4.0])
    assert d.n == 1 and d.mean == 4.0 and d.q1 == 4.0 and d.q3 == 4.0 and d.std == 0.0


def test_distribution_five_number_summary() -> None:
    d = _distribution("x", [1.0, 2.0, 3.0, 4.0, 5.0])
    assert d.minimum == 1.0 and d.maximum == 5.0 and d.median == 3.0
