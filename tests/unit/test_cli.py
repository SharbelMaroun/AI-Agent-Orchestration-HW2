"""CLI shell tests: menu navigation, quit, EOF, unknown options, run-debate
flow, cli() entry-point return codes.

Per-option deep tests (cost report, list/open past debates) live in
`test_cli_actions.py` — split for the 150-LOC test cap (CLAUDE.md §6)."""

from __future__ import annotations

from unittest.mock import MagicMock

from debate.main import cli, run_menu
from tests.unit._cli_fixtures import CapturingWriter, FakeReader, result, verdict


def test_quit_exits_immediately() -> None:
    sdk = MagicMock()
    reader = FakeReader(["q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Goodbye." in writer.all


def test_run_debate_invokes_sdk() -> None:
    """The CLI passes on_event to sdk.run_debate; live events drive the
    transcript print-out (verdict included). The mock simulates the
    orchestrator firing the verdict event."""
    sdk = MagicMock()
    res = result()

    def fake_run(*, on_event, **_kw):
        if on_event is not None:
            on_event("verdict", res.verdict)
        return res

    sdk.run_debate.side_effect = fake_run
    reader = FakeReader(["1", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    sdk.run_debate.assert_called_once()
    assert "Winner: DOGS" in writer.all
    assert "on_event" in sdk.run_debate.call_args.kwargs


def test_view_last_verdict_when_present() -> None:
    sdk = MagicMock()
    sdk.get_last_verdict.return_value = verdict("cats")
    reader = FakeReader(["2", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Winner: CATS" in writer.all


def test_view_last_verdict_when_absent() -> None:
    sdk = MagicMock()
    sdk.get_last_verdict.return_value = None
    reader = FakeReader(["2", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "No verdict yet." in writer.all


def test_unknown_option_falls_through() -> None:
    sdk = MagicMock()
    reader = FakeReader(["zz", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Unknown option" in writer.all


def test_run_debate_catches_exception() -> None:
    sdk = MagicMock()
    sdk.run_debate.side_effect = RuntimeError("API down")
    reader = FakeReader(["1", "q"])
    writer = CapturingWriter()
    run_menu(sdk=sdk, reader=reader, writer=writer)
    assert "Debate failed: API down" in writer.all


def test_eof_treated_as_quit() -> None:
    sdk = MagicMock()

    def raise_eof(_p):
        raise EOFError

    writer = CapturingWriter()
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
