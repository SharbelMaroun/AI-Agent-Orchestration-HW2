"""Pretty-printers for menu output: Verdict / Ping / Score / cost report
+ the on_event callback factory used by the live debate view."""

from __future__ import annotations

from collections.abc import Callable

from debate.shared.schemas import Ping, Score, Verdict


def fmt_verdict(v: Verdict) -> str:
    return (
        f"\nWinner: {v.winner.upper()}\n"
        f"Dogs total: {v.dogs_total} | Cats total: {v.cats_total} "
        f"| Margin: {v.margin}\n"
        f"\nRationale:\n{v.written_rationale}\n"
    )


def fmt_ping(p: Ping) -> str:
    citations = ", ".join(p.citations) if p.citations else "(none)"
    return (
        f"\n--- Round {p.round} | {p.side.upper()} "
        f"(tokens in/out: {p.tokens_in}/{p.tokens_out}) ---\n"
        f"{p.text}\n"
        f"Citations: {citations}"
    )


def fmt_score(s: Score) -> str:
    total = s.structure + s.logos + s.pathos + s.ethos + s.clash
    return (
        f"  Judge -> {s.side} R{s.ping_round}: "
        f"struct={s.structure} logos={s.logos} pathos={s.pathos} "
        f"ethos={s.ethos} clash={s.clash} | total={total}\n"
        f"  Rationale: {s.rationale}"
    )


def print_cost_report(report: dict, writer: Callable[[str], None]) -> None:
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


def live_event_printer(writer: Callable[[str], None]) -> Callable[[str, object], None]:
    """Returns an `on_event` callback that pretty-prints each debate event
    (announcement / ping / score / verdict) as it happens."""

    def callback(kind: str, payload: object) -> None:
        if kind == "announcement" and isinstance(payload, str):
            writer("\n===== JUDGE ANNOUNCEMENT =====")
            writer(payload)
            writer("==============================")
        elif kind == "ping" and isinstance(payload, Ping):
            writer(fmt_ping(payload))
        elif kind == "score" and isinstance(payload, Score):
            writer(fmt_score(payload))
        elif kind == "verdict" and isinstance(payload, Verdict):
            writer("\n===== VERDICT =====")
            writer(fmt_verdict(payload))

    return callback
