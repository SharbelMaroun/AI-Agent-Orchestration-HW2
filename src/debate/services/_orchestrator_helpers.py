"""Stateless helpers used by `Orchestrator` — opening brief factory,
Judge announcement template, JSON persistence, cost-report wiring,
rubric blurb. Extracted so `orchestrator.py` stays under the raw cap."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from debate.shared.pricing import cost_report_from_pings
from debate.shared.schemas import DebateResult, OpeningBrief, Side

if TYPE_CHECKING:
    from debate.shared.schemas import Ping


def make_brief(
    topic: str,
    num_rounds: int,
    rules: str,
    side: str | None,
    rubric: str | None = None,
) -> OpeningBrief:
    return OpeningBrief(
        topic=topic,
        num_rounds=num_rounds,
        rules=rules,
        side=side,
        rubric=rubric,
    )


def rubric_blurb() -> str:
    return "Five dimensions per ping (Structure, Logos, Pathos, Ethos, Clash), 0-3 each."


def make_rules(max_words_per_ping: int) -> str:
    """Build the debate rules string from config so the per-ping word cap is
    sourced from `setup.max_words_per_ping`, not hardcoded (CLAUDE.md §8)."""
    return f"<={max_words_per_ping} words per ping, JSON-only replies, clash required from round 2."


def announcement_text(topic: str, rules: str, num_rounds: int, opener: Side) -> str:
    return (
        f'Judge: Welcome to the debate. Topic: "{topic}". '
        f"Rules: {rules} The debate runs for {num_rounds} round(s). "
        f"Coin flip result: {opener.upper()} will open."
    )


def persist_result(result: DebateResult, results_dir: Path) -> Path:
    """Write `DebateResult` to `results_dir/debate_<YYYYMMDDTHHMMSS>.json`."""
    results_dir.mkdir(parents=True, exist_ok=True)
    ts: datetime = result.started_at
    path = results_dir / f"debate_{ts.strftime('%Y%m%dT%H%M%S')}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def build_cost_report(pings: list[Ping], models: dict, pricing: dict) -> dict:
    """Per-ping token totals + USD cost from `setup.pricing`. Agent-side
    only. Normal SDK runs pass the full gatekeeper summary instead."""
    return cost_report_from_pings(pings, models, pricing)
