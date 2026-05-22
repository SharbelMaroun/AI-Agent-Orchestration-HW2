"""Schema round-trip + validation tests (Phase 3.1)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from debate.shared.schemas import (
    OpeningBrief,
    Ping,
    Score,
    Verdict,
    YourTurn,
)

NOW = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)


def _sample_ping(side="dogs", round_=1):
    return Ping(
        round=round_,
        side=side,
        text="Dogs are loyal.",
        citations=["https://example.com/a"],
        refers_to_ping=None,
        timestamp=NOW,
        tokens_in=10,
        tokens_out=20,
    )


def test_ping_roundtrip_json():
    p = _sample_ping()
    restored = Ping.model_validate_json(p.model_dump_json())
    assert restored == p


def test_score_roundtrip_json():
    s = Score(
        ping_round=1,
        side="cats",
        structure=2,
        logos=1,
        pathos=3,
        ethos=2,
        clash=2,
        rationale="solid open",
    )
    assert Score.model_validate_json(s.model_dump_json()) == s


def test_verdict_roundtrip_json():
    v = Verdict(
        winner="dogs",
        dogs_total=42,
        cats_total=37,
        margin=5,
        written_rationale="dogs clashed harder",
        key_points_dogs=["loyalty", "longevity"],
        key_points_cats=["independence"],
    )
    assert Verdict.model_validate_json(v.model_dump_json()) == v


def test_invalid_side_rejected():
    with pytest.raises(ValidationError):
        _sample_ping(side="hamsters")


def test_envelope_extra_field_rejected():
    """Envelopes use extra='forbid' to catch typos at the receiver."""
    payload = {"type": "YOUR_TURN", "round": 1, "previous_ping": None, "rogue": True}
    with pytest.raises(ValidationError):
        YourTurn.model_validate(payload)


def test_score_dimension_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Score(
            ping_round=1,
            side="dogs",
            structure=4,
            logos=1,
            pathos=1,
            ethos=1,
            clash=1,
            rationale="x",
        )


def test_opening_brief_judge_has_optional_side():
    brief = OpeningBrief(
        topic="cats vs dogs",
        num_rounds=10,
        rules="be brief",
        rubric="5 dims, 0-3",
    )
    assert brief.side is None
    assert brief.type == "OPENING_BRIEF"
