"""Unit tests for debate.main (the terminal-menu CLI)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from debate.main import cli, run_menu
from debate.shared.schemas import DebateResult, Ping, Verdict


def _verdict(winner: str = "dogs") -> Verdict:
    return Verdict(
        winner=winner, dogs_total=10, cats_total=8, margin=2,
        written_rationale="solid case", key_points_dogs=[], key_points_cats=[],
    )


def _result() -> DebateResult:
    now = datetime.now(timezone.utc)
    return DebateResult(
        topic="t", pings=[
            Ping(round=1, side="dogs", text="open", citations=["url"],
                 refers_to_ping=None, timestamp=now, tokens_in=5, tokens_out=5),
        ],
        scores=[], verdict=_verdict(), cost_report={"total_usd": 0.01},
        started_at=now, finished_at=now,
    )


class _FakeReader:
    def __init__(self, inputs: list[str]) -> None:
        self.inputs = list(inputs)
    def __call__(self, _prompt: str) -> str:
        return self.inputs.pop(0)


class _CapturingWriter:
    def __init__(self) -> None:
        self.lines: list[str] = []
    def __call__(self, msg: str) -> None:
        self.lines.append(str(msg))
    @property
    def all(self) -> str:
        return "\n".join(self.lines)


def test_quit_exits_immediately() -> None:
    sdk = MagicMock()
    reader = _FakeReader(["q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Goodbye." in writer.all


def test_run_debate_invokes_sdk() -> None:
    sdk = MagicMock()
    sdk.run_debate.return_value = _result()
    reader = _FakeReader(["1", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    sdk.run_debate.assert_called_once()
    assert "Winner: DOGS" in writer.all


def test_view_last_verdict_when_present() -> None:
    sdk = MagicMock()
    sdk.get_last_verdict.return_value = _verdict("cats")
    reader = _FakeReader(["2", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Winner: CATS" in writer.all


def test_view_last_verdict_when_absent() -> None:
    sdk = MagicMock()
    sdk.get_last_verdict.return_value = None
    reader = _FakeReader(["2", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No verdict yet." in writer.all


def test_view_cost_report() -> None:
    sdk = MagicMock()
    sdk.get_cost_report.return_value = {
        "total_usd": 0.123, "cache_read_pct": 42.0,
        "by_model": {"anthropic/haiku": {
            "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.012,
            "cache_creation_tokens": 0, "cache_read_tokens": 0,
        }},
    }
    reader = _FakeReader(["3", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Total: $0.1230" in writer.all
    assert "42.0%" in writer.all
    assert "anthropic/haiku" in writer.all


def test_view_cost_report_empty() -> None:
    sdk = MagicMock()
    sdk.get_cost_report.return_value = {}
    reader = _FakeReader(["3", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No cost data" in writer.all


def test_list_past_debates_empty() -> None:
    sdk = MagicMock()
    sdk.list_past_debates.return_value = []
    reader = _FakeReader(["4", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No past debates found." in writer.all


def test_list_past_debates_some(tmp_path) -> None:
    p = tmp_path / "debate_x.json"
    p.write_text("{}", encoding="utf-8")
    sdk = MagicMock()
    sdk.list_past_debates.return_value = [p]
    reader = _FakeReader(["4", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "debate_x.json" in writer.all


def test_unknown_option_falls_through() -> None:
    sdk = MagicMock()
    reader = _FakeReader(["zz", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Unknown option" in writer.all


def test_run_debate_catches_exception() -> None:
    sdk = MagicMock()
    sdk.run_debate.side_effect = RuntimeError("API down")
    reader = _FakeReader(["1", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Debate failed: API down" in writer.all


def test_eof_treated_as_quit() -> None:
    sdk = MagicMock()
    def raise_eof(_p):
        raise EOFError
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=raise_eof, writer=writer)
    assert "Goodbye." in writer.all


def test_cli_keyboard_interrupt_returns_130(monkeypatch) -> None:
    import debate.main as main_mod
    def boom(**_kw):
        raise KeyboardInterrupt
    monkeypatch.setattr(main_mod, "run_menu", boom)
    assert cli() == 130


def test_cli_normal_exit_returns_0(monkeypatch) -> None:
    import debate.main as main_mod
    monkeypatch.setattr(main_mod, "run_menu", lambda **_kw: None)
    assert cli() == 0


@pytest.fixture
def _seed_past_debate(tmp_path):
    """A real DebateResult JSON file the 'open past debate' branch can load."""
    payload = _result().model_dump(mode="json")
    p = tmp_path / "debate_20260522T000000.json"
    import json as _json
    p.write_text(_json.dumps(payload), encoding="utf-8")
    return p


def test_open_past_debate_selects_and_prints(monkeypatch, _seed_past_debate) -> None:
    sdk = MagicMock()
    sdk.list_past_debates.return_value = [_seed_past_debate]
    inputs = iter(["5", "1", "q"])
    writer = _CapturingWriter()
    monkeypatch.setattr("builtins.input", lambda _p="": next(inputs))
    run_menu(sdk=sdk, reader=lambda _p: next(inputs), writer=writer)
    assert "Topic: t" in writer.all
    assert "Winner: DOGS" in writer.all


def test_open_past_debate_empty() -> None:
    sdk = MagicMock()
    sdk.list_past_debates.return_value = []
    reader = _FakeReader(["5", "q"])
    writer = _CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No past debates found." in writer.all
