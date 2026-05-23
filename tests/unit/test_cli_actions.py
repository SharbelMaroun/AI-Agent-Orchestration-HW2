"""Per-menu-option tests: cost report (option 3), list past debates
(option 4), open past debate transcript (option 5).

Split off from `test_cli.py` for the 150-LOC test cap."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from debate.main import run_menu
from tests.unit._cli_fixtures import CapturingWriter, FakeReader, result


def test_view_cost_report() -> None:
    sdk = MagicMock()
    sdk.get_cost_report.return_value = {
        "total_usd": 0.123,
        "cache_read_pct": 42.0,
        "by_model": {
            "anthropic/haiku": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cost_usd": 0.012,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
            }
        },
    }
    reader = FakeReader(["3", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Total: $0.1230" in writer.all
    assert "42.0%" in writer.all
    assert "anthropic/haiku" in writer.all


def test_view_cost_report_empty() -> None:
    sdk = MagicMock()
    sdk.get_cost_report.return_value = {}
    reader = FakeReader(["3", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No cost data" in writer.all


def test_list_past_debates_empty() -> None:
    sdk = MagicMock()
    sdk.list_past_debates.return_value = []
    reader = FakeReader(["4", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No past debates found." in writer.all


def test_list_past_debates_some(tmp_path, monkeypatch) -> None:
    """Option 4 now lists numbered debates AND prompts for selection (blank
    cancels). Empty input from the inner input() returns to the menu."""
    p = tmp_path / "debate_x.json"
    p.write_text("{}", encoding="utf-8")
    sdk = MagicMock()
    sdk.list_past_debates.return_value = [p]
    monkeypatch.setattr("builtins.input", lambda _p="": "")  # cancel selection
    reader = FakeReader(["4", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "debate_x.json" in writer.all


@pytest.fixture
def _seed_past_debate(tmp_path):
    """A real DebateResult JSON file the 'open past debate' branch can load."""
    payload = result().model_dump(mode="json")
    p = tmp_path / "debate_20260522T000000.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_open_past_debate_selects_and_prints(monkeypatch, _seed_past_debate) -> None:
    sdk = MagicMock()
    sdk.list_past_debates.return_value = [_seed_past_debate]
    inputs = iter(["5", "1", "q"])
    writer = CapturingWriter()
    monkeypatch.setattr("builtins.input", lambda _p="": next(inputs))
    run_menu(sdk=sdk, reader=lambda _p: next(inputs), writer=writer)
    assert "Topic: t" in writer.all
    assert "Winner: DOGS" in writer.all


def test_open_past_debate_empty() -> None:
    sdk = MagicMock()
    sdk.list_past_debates.return_value = []
    reader = FakeReader(["5", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No past debates found." in writer.all
