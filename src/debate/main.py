"""CLI entry point — terminal menu for running debates.

Keyboard-driven menu per PRD §4.3 — runs in any terminal, no GUI deps.
All business logic is delegated to `DebateSDK`; this file is presentation
only (CLAUDE.md §4: no business logic in CLI/GUI layers).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable

from debate.sdk.sdk import DebateSDK
from debate.shared.schemas import DebateResult, Ping, Score, Verdict

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


def _fmt_verdict(v: Verdict) -> str:
    return (
        f"\nWinner: {v.winner.upper()}\n"
        f"Dogs total: {v.dogs_total} | Cats total: {v.cats_total} "
        f"| Margin: {v.margin}\n"
        f"\nRationale:\n{v.written_rationale}\n"
    )


def _fmt_ping(p: Ping) -> str:
    citations = ", ".join(p.citations) if p.citations else "(none)"
    return (
        f"\n--- Round {p.round} | {p.side.upper()} "
        f"(tokens in/out: {p.tokens_in}/{p.tokens_out}) ---\n"
        f"{p.text}\n"
        f"Citations: {citations}"
    )


def _fmt_score(s: Score) -> str:
    total = s.structure + s.logos + s.pathos + s.ethos + s.clash
    return (
        f"  Judge -> {s.side} R{s.ping_round}: "
        f"struct={s.structure} logos={s.logos} pathos={s.pathos} "
        f"ethos={s.ethos} clash={s.clash} | total={total}\n"
        f"  Rationale: {s.rationale}"
    )


def _live_event_printer(writer: Callable[[str], None]) -> Callable[[str, object], None]:
    """Returns an on_event callback that pretty-prints each debate event as
    it happens — pings, scores, and the final verdict."""

    def callback(kind: str, payload: object) -> None:
        if kind == "announcement" and isinstance(payload, str):
            writer("\n===== JUDGE ANNOUNCEMENT =====")
            writer(payload)
            writer("==============================")
        elif kind == "ping" and isinstance(payload, Ping):
            writer(_fmt_ping(payload))
        elif kind == "score" and isinstance(payload, Score):
            writer(_fmt_score(payload))
        elif kind == "verdict" and isinstance(payload, Verdict):
            writer("\n===== VERDICT =====")
            writer(_fmt_verdict(payload))

    return callback


def _print_cost_report(report: dict, writer: Callable[[str], None]) -> None:
    if not report:
        writer("No cost data available — run a debate first.")
        return
    writer(f"\nTotal: ${report.get('total_usd', 0):.4f}")
    writer(f"Cache read share: {report.get('cache_read_pct', 0):.1f}%")
    writer("\nBy model:")
    for model, stats in (report.get("by_model") or {}).items():
        writer(
            f"  {model}: in={stats['input_tokens']} "
            f"out={stats['output_tokens']} cost=${stats['cost_usd']:.4f}"
        )


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
        idx = int(choice) - 1
        target = debates[idx]
    except (ValueError, IndexError):
        writer("Invalid selection.")
        return
    payload = json.loads(target.read_text(encoding="utf-8"))
    result = DebateResult.model_validate(payload)
    writer(f"\nTopic: {result.topic}")
    # Match the live-stream layout: each ping immediately followed by the
    # judge's per-dimension score for that same (round, side).
    scores_by_key = {(s.ping_round, s.side): s for s in result.scores}
    for ping in result.pings:
        writer(_fmt_ping(ping))
        score = scores_by_key.get((ping.round, ping.side))
        if score is not None:
            writer(_fmt_score(score))
    writer(_fmt_verdict(result.verdict))


def run_menu(
    sdk: DebateSDK | None = None,
    reader: Callable[[str], str] = input,
    writer: Callable[[str], None] = print,
) -> None:
    """The main menu loop. `sdk`, `reader`, and `writer` are injected for tests."""
    sdk = sdk or DebateSDK()
    writer(BANNER)
    while True:
        writer(MENU)
        choice = _prompt(reader)
        if choice == "q":
            writer("Goodbye.")
            return
        if choice == "1":
            writer(
                "Running debate — pings and judge scores will print live as each round completes..."
            )
            try:
                sdk.run_debate(on_event=_live_event_printer(writer))
            except Exception as exc:  # noqa: BLE001
                writer(f"Debate failed: {exc}")
                continue
        elif choice == "2":
            verdict = sdk.get_last_verdict()
            writer(_fmt_verdict(verdict) if verdict else "No verdict yet.")
        elif choice == "3":
            _print_cost_report(sdk.get_cost_report(), writer)
        elif choice in ("4", "5"):  # "5" kept as alias for the old menu
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
