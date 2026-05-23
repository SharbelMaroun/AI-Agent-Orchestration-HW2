"""JudgeAgent integration tests: scoring, decide_winner, receive dispatch.

Pure-helper tests (tie-break, collusion, total math, key-points,
JSON extract, prompt load) live in `test_judge_helpers.py` — split for
the 150-LOC test cap (CLAUDE.md §6)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from debate.services.agents.judge_agent import FinalizeRequest, JudgeAgent
from debate.shared.schemas import CompletionResponse, Ping, Score, Verdict

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


def _passthrough_gk():
    gk = MagicMock()
    gk.execute.side_effect = lambda fn, *a, **kw: fn(*a, **kw)
    return gk


def _provider(text: str):
    p = MagicMock()
    p.complete = MagicMock(
        return_value=CompletionResponse(
            text=text,
            input_tokens=1,
            output_tokens=1,
            model="m",
            provider="anthropic",
        )
    )
    return p


def _judge(text='{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'):
    return JudgeAgent(
        provider=_provider(text),
        gatekeeper=_passthrough_gk(),
        model_name="m",
        system_prompt="be fair",
    )


def _ping(side="dogs", round_=1, text="claim with evidence"):
    return Ping(round=round_, side=side, text=text, timestamp=NOW)


def _full_score(side: str, val: int) -> Score:
    return Score(
        ping_round=1,
        side=side,
        structure=val,
        logos=val,
        pathos=val,
        ethos=val,
        clash=val,
        rationale="",
    )


def test_score_ping_returns_valid_score() -> None:
    j = _judge()
    s = j.score_ping(_ping())
    assert isinstance(s, Score)
    assert s.ping_round == 1 and s.side == "dogs"
    assert j.scores[-1] is s


def test_decide_winner_no_tie() -> None:
    j = _judge()
    j.scores = [_full_score("dogs", 3), _full_score("cats", 1)]
    j.provider.complete.return_value = CompletionResponse(
        text='{"winner":"dogs","written_rationale":"dogs clashed harder"}',
        input_tokens=1,
        output_tokens=1,
        model="m",
        provider="anthropic",
    )
    v = j.decide_winner(pings=[_ping(side="dogs"), _ping(side="cats")])
    assert isinstance(v, Verdict)
    assert v.winner == "dogs"
    assert v.dogs_total == 15 and v.cats_total == 5
    assert v.margin == 10


def test_decide_winner_breaks_tie() -> None:
    """Equal totals (10 each) but dogs has higher clash → tie-break picks dogs
    even though the LLM said cats."""
    j = _judge()
    j.scores = [
        Score(
            ping_round=1,
            side="dogs",
            structure=2,
            logos=2,
            pathos=1,
            ethos=2,
            clash=3,
            rationale="",
        ),
        Score(
            ping_round=1,
            side="cats",
            structure=2,
            logos=2,
            pathos=3,
            ethos=2,
            clash=1,
            rationale="",
        ),
    ]
    j.provider.complete.return_value = CompletionResponse(
        text='{"winner":"cats","written_rationale":"placeholder"}',
        input_tokens=1,
        output_tokens=1,
        model="m",
        provider="anthropic",
    )
    v = j.decide_winner(pings=[_ping(side="dogs"), _ping(side="cats")])
    assert v.winner == "dogs"
    assert v.margin == 0


def test_receive_ping_scores() -> None:
    j = _judge()
    out = j.receive(_ping())
    assert isinstance(out, Score)


def test_receive_finalize_returns_verdict() -> None:
    j = _judge()
    j.scores = [_full_score("dogs", 3), _full_score("cats", 0)]
    j.provider.complete.return_value = CompletionResponse(
        text='{"winner":"dogs","written_rationale":"clear"}',
        input_tokens=1,
        output_tokens=1,
        model="m",
        provider="anthropic",
    )
    out = j.receive(FinalizeRequest(pings=[_ping()]))
    assert isinstance(out, Verdict)
