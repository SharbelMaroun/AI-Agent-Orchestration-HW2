"""JudgeAgent tests (Phase 3.8)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from debate.services.agents.judge_agent import FinalizeRequest, JudgeAgent
from debate.shared.schemas import CompletionResponse, Ping, Score, Verdict

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)


def _passthrough_gk():
    gk = MagicMock()
    gk.execute.side_effect = lambda fn, *a, **kw: fn(*a, **kw)
    return gk


def _provider_with_text(text: str):
    p = MagicMock()
    p.complete = MagicMock(return_value=CompletionResponse(
        text=text, input_tokens=1, output_tokens=1, model="m", provider="anthropic",
    ))
    return p


def _judge(text='{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'):
    return JudgeAgent(
        provider=_provider_with_text(text),
        gatekeeper=_passthrough_gk(),
        model_name="m",
        system_prompt="be fair",
    )


def _ping(side="dogs", round_=1, text="claim with evidence"):
    return Ping(round=round_, side=side, text=text, timestamp=NOW)


def test_judge_loads_default_prompt_file():
    j = JudgeAgent(provider=_provider_with_text("{}"), gatekeeper=_passthrough_gk(), model_name="m")
    assert "JUDGE" in j.system_prompt.upper()


def test_score_ping_returns_valid_score():
    j = _judge()
    s = j.score_ping(_ping())
    assert isinstance(s, Score)
    assert s.ping_round == 1 and s.side == "dogs"
    assert j.scores[-1] is s


def test_concession_forces_clash_zero():
    j = _judge('{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":3,"rationale":"x"}')
    s = j.score_ping(_ping(text="You make a good point and dogs are loyal."))
    assert s.clash == 0


def test_total_helper():
    s = Score(ping_round=1, side="dogs", structure=1, logos=2, pathos=3, ethos=1, clash=2, rationale="x")
    assert JudgeAgent._total(s) == 9


def test_tiebreak_prefers_higher_clash():
    j = _judge()
    j.scores = [
        Score(ping_round=1, side="dogs", structure=0, logos=0, pathos=0, ethos=0, clash=3, rationale=""),
        Score(ping_round=1, side="cats", structure=0, logos=0, pathos=0, ethos=0, clash=1, rationale=""),
    ]
    assert j._tie_break() == "dogs"


def test_tiebreak_falls_through_to_pathos():
    j = _judge()
    j.scores = [
        Score(ping_round=1, side="dogs", structure=0, logos=0, pathos=1, ethos=0, clash=2, rationale=""),
        Score(ping_round=1, side="cats", structure=0, logos=0, pathos=3, ethos=0, clash=2, rationale=""),
    ]
    assert j._tie_break() == "cats"


def test_detect_collusion_threshold():
    pings = [
        _ping(text="i agree completely"),
        _ping(text="fair enough, you are right"),
        _ping(text="you make a good case"),
    ]
    assert JudgeAgent._detect_collusion(pings) is True


def test_detect_collusion_not_triggered_when_one_substantive():
    pings = [
        _ping(text="i agree"),
        _ping(text="dogs are loyal because of evidence X"),
        _ping(text="you're right"),
    ]
    assert JudgeAgent._detect_collusion(pings) is False


def test_extract_key_points_first_sentences():
    pings = [
        _ping(side="dogs", text="Dogs reduce stress. They also live with us."),
        _ping(side="cats", text="Cats are independent."),
        _ping(side="dogs", text="Working dogs save lives."),
    ]
    pts = JudgeAgent._extract_key_points(pings, "dogs", k=2)
    assert pts == ["Dogs reduce stress", "Working dogs save lives"]


def test_decide_winner_no_tie():
    j = _judge()
    j.scores = [
        Score(ping_round=1, side="dogs", structure=3, logos=3, pathos=3, ethos=3, clash=3, rationale=""),
        Score(ping_round=1, side="cats", structure=1, logos=1, pathos=1, ethos=1, clash=1, rationale=""),
    ]
    j.provider.complete.return_value = CompletionResponse(
        text='{"winner":"dogs","written_rationale":"dogs clashed harder"}',
        input_tokens=1, output_tokens=1, model="m", provider="anthropic",
    )
    v = j.decide_winner(pings=[_ping(side="dogs"), _ping(side="cats")])
    assert isinstance(v, Verdict)
    assert v.winner == "dogs"
    assert v.dogs_total == 15 and v.cats_total == 5
    assert v.margin == 10


def test_decide_winner_breaks_tie():
    j = _judge()
    # Equal totals (10 each) but dogs has more clash
    j.scores = [
        Score(ping_round=1, side="dogs", structure=2, logos=2, pathos=1, ethos=2, clash=3, rationale=""),
        Score(ping_round=1, side="cats", structure=2, logos=2, pathos=3, ethos=2, clash=1, rationale=""),
    ]
    j.provider.complete.return_value = CompletionResponse(
        text='{"winner":"cats","written_rationale":"placeholder"}',  # LLM says cats
        input_tokens=1, output_tokens=1, model="m", provider="anthropic",
    )
    v = j.decide_winner(pings=[_ping(side="dogs"), _ping(side="cats")])
    # tie-break overrides LLM, picks dogs (higher clash)
    assert v.winner == "dogs"
    assert v.margin == 0


def test_receive_ping_scores():
    j = _judge()
    out = j.receive(_ping())
    assert isinstance(out, Score)


def test_receive_finalize_returns_verdict():
    j = _judge()
    j.scores = [
        Score(ping_round=1, side="dogs", structure=3, logos=3, pathos=3, ethos=3, clash=3, rationale=""),
        Score(ping_round=1, side="cats", structure=0, logos=0, pathos=0, ethos=0, clash=0, rationale=""),
    ]
    j.provider.complete.return_value = CompletionResponse(
        text='{"winner":"dogs","written_rationale":"clear"}',
        input_tokens=1, output_tokens=1, model="m", provider="anthropic",
    )
    out = j.receive(FinalizeRequest(pings=[_ping()]))
    assert isinstance(out, Verdict)


def test_extract_json_missing_raises():
    with pytest.raises(ValueError, match="no JSON"):
        JudgeAgent._extract_json("plain text only")
