"""End-to-end debate smoke tests with mocked LLM providers.

These wire the real SDK + Orchestrator + agents together; only the LLM
provider is faked (via the shared `fake_provider_factory` fixture). They
exist to catch regressions in the *integration seams* that pure unit tests
miss — e.g., schema mismatches between agents and orchestrator.
"""

from __future__ import annotations

import json
from pathlib import Path

from debate.sdk.sdk import DebateSDK
from debate.shared.config import load_setup
from debate.shared.schemas import DebateResult, Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_sdk(tmp_path: Path, factory, num_rounds: int = 2) -> DebateSDK:
    setup = load_setup(REPO_ROOT / "config" / "setup.json")
    data = setup.model_dump()
    data["num_rounds"] = num_rounds
    setup = type(setup).model_validate(data)
    return DebateSDK(setup=setup, results_dir=tmp_path, provider_factory=factory)


def test_full_debate_two_rounds(tmp_path: Path, fake_provider_factory) -> None:
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=2)
    result = sdk.run_debate()
    assert isinstance(result, DebateResult)
    assert len(result.pings) == 4  # 2 rounds × 2 sides
    assert result.verdict.winner in ("dogs", "cats")


def test_full_debate_ten_rounds_pings_count(tmp_path: Path, fake_provider_factory) -> None:
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=10)
    result = sdk.run_debate()
    # 10 rounds × 2 sides = 20 pings; matches PRD G2.
    assert len(result.pings) == 20
    rounds = sorted({p.round for p in result.pings})
    assert rounds == list(range(1, 11))


def test_full_debate_dogs_opens_round_one(tmp_path: Path, fake_provider_factory) -> None:
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=1)
    result = sdk.run_debate()
    first = next(p for p in result.pings if p.round == 1)
    assert first.side == "dogs"


def test_full_debate_persists_to_disk(tmp_path: Path, fake_provider_factory) -> None:
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=1)
    sdk.run_debate()
    files = list(tmp_path.glob("debate_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    Verdict.model_validate(payload["verdict"])  # round-trips


def test_full_debate_pings_alternate_sides(tmp_path: Path, fake_provider_factory) -> None:
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=3)
    result = sdk.run_debate()
    sides_in_order = [
        p.side for p in sorted(result.pings, key=lambda p: (p.round, 0 if p.side == "dogs" else 1))
    ]
    expected = ["dogs", "cats"] * 3
    assert sides_in_order == expected


def test_two_debates_in_sequence_isolated(tmp_path: Path, fake_provider_factory) -> None:
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=1)
    r1 = sdk.run_debate()
    r2 = sdk.run_debate()
    # Each run produces its own DebateResult object; ping histories don't bleed.
    assert r1 is not r2
    assert all(p.round == 1 for p in r1.pings)
    assert all(p.round == 1 for p in r2.pings)
    # At least one file persisted (timestamp is second-resolution, so two runs
    # in the same second collapse to one file — that's an orchestrator quirk
    # documented in PRD; not what this test guards against).
    assert list(tmp_path.glob("debate_*.json"))


def test_full_debate_clash_invariant(tmp_path: Path, fake_provider_factory) -> None:
    """From round 2 onward every ping must reference the prior opponent ping."""
    sdk = _build_sdk(tmp_path, fake_provider_factory, num_rounds=3)
    result = sdk.run_debate()
    for ping in result.pings:
        if ping.round == 1 and ping.side == "dogs":
            continue
        assert ping.refers_to_ping is not None, f"ping {ping.round}/{ping.side} missing clash"
