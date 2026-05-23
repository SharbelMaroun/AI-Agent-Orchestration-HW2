"""Pure-helper tests for JudgeAgent: prompt loading, concession detection,
tie-break + total math, key-point extraction, JSON extraction.

Split off from `test_judge_agent.py` to honour the 150-LOC test cap
(CLAUDE.md §6). The "scoring + verdict integration" tests live in
`test_judge_agent.py`; this file is the static-method battery."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from debate.services.agents.judge_agent import JudgeAgent
from debate.shared.schemas import CompletionResponse, Ping, Score

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


def _judge(text: str = '{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'):
    return JudgeAgent(
        provider=_provider(text),
        gatekeeper=_passthrough_gk(),
        model_name="m",
        system_prompt="be fair",
    )


def _ping(side: str = "dogs", round_: int = 1, text: str = "claim with evidence") -> Ping:
    return Ping(round=round_, side=side, text=text, timestamp=NOW)


def _score(side: str, **kw) -> Score:
    defaults = {
        "ping_round": 1,
        "side": side,
        "structure": 0,
        "logos": 0,
        "pathos": 0,
        "ethos": 0,
        "clash": 0,
        "rationale": "",
    }
    defaults.update(kw)
    return Score(**defaults)


def test_judge_loads_default_prompt_file() -> None:
    j = JudgeAgent(provider=_provider("{}"), gatekeeper=_passthrough_gk(), model_name="m")
    assert "JUDGE" in j.system_prompt.upper()


def test_total_helper() -> None:
    s = _score("dogs", structure=1, logos=2, pathos=3, ethos=1, clash=2, rationale="x")
    assert JudgeAgent._total(s) == 9


def test_tiebreak_prefers_higher_clash() -> None:
    j = _judge()
    j.scores = [_score("dogs", clash=3), _score("cats", clash=1)]
    assert j._tie_break() == "dogs"


def test_tiebreak_falls_through_to_pathos() -> None:
    j = _judge()
    j.scores = [_score("dogs", pathos=1, clash=2), _score("cats", pathos=3, clash=2)]
    assert j._tie_break() == "cats"


def test_detect_collusion_threshold() -> None:
    pings = [
        _ping(text="i agree completely"),
        _ping(text="fair enough, you are right"),
        _ping(text="you make a good case"),
    ]
    assert JudgeAgent._detect_collusion(pings) is True


def test_detect_collusion_not_triggered_when_one_substantive() -> None:
    pings = [
        _ping(text="i agree"),
        _ping(text="dogs are loyal because of evidence X"),
        _ping(text="you're right"),
    ]
    assert JudgeAgent._detect_collusion(pings) is False


def test_extract_key_points_first_sentences() -> None:
    pings = [
        _ping(side="dogs", text="Dogs reduce stress. They also live with us."),
        _ping(side="cats", text="Cats are independent."),
        _ping(side="dogs", text="Working dogs save lives."),
    ]
    pts = JudgeAgent._extract_key_points(pings, "dogs", k=2)
    assert pts == ["Dogs reduce stress", "Working dogs save lives"]


def test_extract_json_missing_raises() -> None:
    with pytest.raises(ValueError, match="no JSON"):
        JudgeAgent._extract_json("plain text only")


def test_concession_forces_clash_zero() -> None:
    j = _judge('{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":3,"rationale":"x"}')
    s = j.score_ping(_ping(text="You make a good point and dogs are loyal."))
    assert s.clash == 0
