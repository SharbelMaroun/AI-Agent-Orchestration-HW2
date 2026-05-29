"""Tests for the sensitivity runner, SDK exposure, and analysis config loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from debate.services.analysis import build_report, save_report
from debate.shared.config import load_setup

from ._sdk_fixtures import REPO_ROOT, build_sdk


def _setup():
    return load_setup(REPO_ROOT / "config" / "setup.json")


def test_config_has_analysis_block() -> None:
    a = _setup().analysis
    assert a is not None
    assert a.token_model.tokens_per_word > 0
    assert "num_rounds" in a.factors and len(a.factors["num_rounds"]) >= 2


def test_build_report_returns_ranked_factors() -> None:
    report = build_report(_setup(), "cost_usd")
    assert report.metric == "cost_usd"
    ranges = [f.metric_range for f in report.factors]
    assert ranges == sorted(ranges, reverse=True)  # tornado order


def test_build_report_raises_without_analysis_block() -> None:
    setup = _setup().model_copy(update={"analysis": None})
    with pytest.raises(ValueError, match="analysis"):
        build_report(setup, "cost_usd")


def test_save_report_writes_parseable_json(tmp_path: Path) -> None:
    report = build_report(_setup(), "total_tokens")
    path = save_report(report, tmp_path, "report.json")
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["metric"] == "total_tokens"
    assert isinstance(payload["factors"], list) and payload["factors"]


def test_sdk_run_sensitivity_analysis(tmp_path: Path) -> None:
    sdk = build_sdk(tmp_path, num_rounds=1)
    report = sdk.run_sensitivity_analysis("cost_usd")
    assert report.factors
    assert report.factors[0].metric_range >= report.factors[-1].metric_range


def test_sdk_empirical_summary_empty(tmp_path: Path) -> None:
    sdk = build_sdk(tmp_path)
    assert sdk.empirical_summary().n_debates == 0


def test_sdk_empirical_summary_after_run(tmp_path: Path) -> None:
    sdk = build_sdk(tmp_path, num_rounds=1)
    sdk.run_debate()
    stats = sdk.empirical_summary()
    assert stats.n_debates == 1
    assert 0.0 <= stats.dogs_win_rate <= 1.0
