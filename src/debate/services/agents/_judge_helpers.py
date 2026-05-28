"""Pure helpers extracted from JudgeAgent.

Split out to keep `judge_agent.py` comfortably under the 150-LOC cap
(CLAUDE.md §4). Every function here is stateless and dependency-free —
the judge module composes them but does not own them."""

from __future__ import annotations

from debate.shared.schemas import Ping, Score, Side

CONCESSION_PHRASES = (
    "good point",
    "fair enough",
    "i agree",
    "you're right",
    "i concede",
    "valid point",
    "you make a good",
)


def is_concession(text: str) -> bool:
    low = text.lower()
    return any(phrase in low for phrase in CONCESSION_PHRASES)


def detect_collusion(recent_pings: list[Ping], window: int = 3) -> bool:
    """Three consecutive concessions = collusion warning."""
    if len(recent_pings) < window:
        return False
    return all(is_concession(p.text) for p in recent_pings[-window:])


def extract_key_points(pings: list[Ping], side: Side, k: int = 3) -> list[str]:
    """Fallback if the LLM verdict didn't supply them — take the first
    sentence of the top-k pings for the side."""
    out: list[str] = []
    for p in pings:
        if p.side != side:
            continue
        first = p.text.split(".")[0].strip()
        if first:
            out.append(first[:80])
        if len(out) >= k:
            break
    return out


def tie_break(scores: list[Score]) -> tuple[Side, str]:
    """Per PRD §6: cascade clash → pathos → dogs-by-convention.

    Returns `(winner, explanation)`. The explanation is the single source of
    truth for *why* the tie was broken; `decide_winner` injects it into
    `written_rationale` so the human-readable text matches the recorded
    winner (a prior bug — the LLM could author a rationale favouring the
    losing side because it ran before the deterministic override)."""
    dogs_clash = sum(s.clash for s in scores if s.side == "dogs")
    cats_clash = sum(s.clash for s in scores if s.side == "cats")
    if dogs_clash != cats_clash:
        winner: Side = "dogs" if dogs_clash > cats_clash else "cats"
        return winner, _explain("Clash", dogs_clash, cats_clash, winner)
    dogs_pathos = sum(s.pathos for s in scores if s.side == "dogs")
    cats_pathos = sum(s.pathos for s in scores if s.side == "cats")
    if dogs_pathos != cats_pathos:
        winner = "dogs" if dogs_pathos > cats_pathos else "cats"
        return winner, _explain("Pathos", dogs_pathos, cats_pathos, winner)
    return "dogs", (
        "Tie-break applied: scores fully tied on Clash and Pathos; "
        "dogs wins by opener convention (PRD §6)."
    )


def _explain(dim: str, dogs_val: int, cats_val: int, winner: Side) -> str:
    w_val, l_val = (dogs_val, cats_val) if winner == "dogs" else (cats_val, dogs_val)
    return (
        f"Tie-break applied: totals were tied, so {winner} wins on higher "
        f"cumulative {dim} ({w_val} vs {l_val})."
    )
