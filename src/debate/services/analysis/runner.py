"""Thin orchestration for the sensitivity study: build a report from a
``SetupConfig`` and persist it. Keeps the SDK facade slim — the SDK delegates
here so all the wiring lives in the service layer, not the entry point.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from debate.shared.config import SetupConfig

from ._models import SensitivityReport
from .sensitivity import economics_evaluator, run_oat


def build_report(setup: SetupConfig, metric: str = "cost_usd") -> SensitivityReport:
    """Run the OAT sweep defined by ``setup.analysis`` for one target metric."""
    cfg = setup.analysis
    if cfg is None:
        raise ValueError("config/setup.json has no 'analysis' block; cannot run sensitivity study")
    evaluate = economics_evaluator(cfg.token_model, setup.pricing)
    baseline = {
        "num_rounds": cfg.baseline.num_rounds,
        "max_words_per_ping": cfg.baseline.max_words_per_ping,
        "model": cfg.baseline.model,
        "cache_read_pct": cfg.baseline.cache_read_pct,
    }
    return run_oat(baseline=baseline, factors=cfg.factors, evaluate=evaluate, metric=metric)


def save_report(report: SensitivityReport, out_dir: str | Path, filename: str) -> Path:
    """Persist a report as pretty JSON under ``out_dir`` and return its path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
    return path
