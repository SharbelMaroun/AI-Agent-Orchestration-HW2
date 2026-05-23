"""CLI entry point — terminal menu for running debates.

Keyboard-driven menu per PRD §4.3 — runs in any terminal, no GUI deps.
All business logic is delegated to `DebateSDK`; this file is presentation
only (CLAUDE.md §4: no business logic in GUI/CLI layers). Pretty-printing
helpers live in `debate.cli.formatters`.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable

from debate.cli.formatters import (
    fmt_ping,
    fmt_score,
    fmt_verdict,
    live_event_printer,
    print_cost_report,
)
from debate.sdk.sdk import DebateSDK
from debate.shared.schemas import DebateResult

BANNER = """\
==============================================================
  AI Agent Orchestration HW2 — Dogs vs Cats Debate
==============================================================
"""

MENU = """\
  [1] Run a new debate
  [2] View last verdict
  [3] View cost report
  [4] List past debates (pick one to open its transcript)
  [Q] Quit
"""


def _prompt(reader: Callable[[str], str] = input) -> str:
    try:
        return reader("Choose an option > ").strip().lower()
    except EOFError:
        return "q"


def _open_past_debate(sdk: DebateSDK, writer: Callable[[str], None]) -> None:
    debates = sdk.list_past_debates()
    if not debates:
        writer("No past debates found.")
        return
    for i, path in enumerate(debates, 1):
        writer(f"  [{i}] {path.name}")
    choice = input("Pick a number (or blank to cancel) > ").strip()
    if not choice:
        return
    try:
        target = debates[int(choice) - 1]
    except (ValueError, IndexError):
        writer("Invalid selection.")
        return
    result = DebateResult.model_validate(json.loads(target.read_text(encoding="utf-8")))
    writer(f"\nTopic: {result.topic}")
    scores_by_key = {(s.ping_round, s.side): s for s in result.scores}
    for ping in result.pings:
        writer(fmt_ping(ping))
        score = scores_by_key.get((ping.round, ping.side))
        if score is not None:
            writer(fmt_score(score))
    writer(fmt_verdict(result.verdict))


def run_menu(
    sdk: DebateSDK | None = None,
    reader: Callable[[str], str] = input,
    writer: Callable[[str], None] = print,
) -> None:
    """Main menu loop. `sdk`, `reader`, `writer` injected for tests."""
    sdk = sdk or DebateSDK()
    writer(BANNER)
    while True:
        writer(MENU)
        choice = _prompt(reader)
        if choice == "q":
            writer("Goodbye.")
            return
        if choice == "1":
            writer("Running debate — pings and judge scores will print live...")
            try:
                sdk.run_debate(on_event=live_event_printer(writer))
            except Exception as exc:  # noqa: BLE001
                writer(f"Debate failed: {exc}")
                continue
        elif choice == "2":
            verdict = sdk.get_last_verdict()
            writer(fmt_verdict(verdict) if verdict else "No verdict yet.")
        elif choice == "3":
            print_cost_report(sdk.get_cost_report(), writer)
        elif choice in ("4", "5"):  # "5" silent alias for the old menu
            _open_past_debate(sdk, writer)
        else:
            writer(f"Unknown option: {choice!r}")


def cli(argv: list[str] | None = None) -> int:
    del argv
    try:
        run_menu()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(cli())
