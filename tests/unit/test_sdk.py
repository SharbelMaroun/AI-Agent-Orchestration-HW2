"""DebateSDK tests (Phase 3.10)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from debate.sdk.sdk import DebateSDK
from debate.shared.config import load_setup
from debate.shared.schemas import CompletionResponse, DebateResult, Verdict

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)
REPO_ROOT = Path(__file__).resolve().parents[2]


def _fake_provider_factory(side_to_reply: dict[str, str] | None = None):
    """Return a factory that yields a MagicMock provider with a canned reply
    suitable for any DogsAgent / CatsAgent / JudgeAgent call."""
    default_score = '{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'
    default_verdict = '{"winner":"dogs","written_rationale":"clear"}'
    import re as _re

    opp_round_re = _re.compile(r"Opponent's previous ping \(round (\d+)")

    def factory(_name: str):
        provider = MagicMock()

        def complete(*, system, messages, model, max_tokens):
            del max_tokens
            last_user = messages[-1].content if messages else ""
            low = last_user.lower()
            if "final scores" in low or "deliver the verdict" in low:
                text = default_verdict
            elif "score this ping" in low:
                text = default_score
            else:
                m = opp_round_re.search(last_user)
                refers = m.group(1) if m else "null"
                text = f'{{"text":"argued","citations":[],"refers_to_ping":{refers}}}'
            return CompletionResponse(
                text=text,
                input_tokens=5,
                output_tokens=5,
                model=model,
                provider="anthropic",
            )

        provider.complete.side_effect = complete
        return provider

    return factory


def _sdk(tmp_path: Path, num_rounds: int = 2) -> DebateSDK:
    setup = load_setup(REPO_ROOT / "config" / "setup.json")
    # Shrink rounds to keep tests fast; SetupConfig is a Pydantic model so we
    # round-trip through a dict to mutate it cleanly.
    data = setup.model_dump()
    data["num_rounds"] = num_rounds
    setup = type(setup).model_validate(data)
    return DebateSDK(
        setup=setup,
        results_dir=tmp_path,
        provider_factory=_fake_provider_factory(),
    )


def test_sdk_run_debate_returns_result(tmp_path: Path):
    sdk = _sdk(tmp_path, num_rounds=1)
    result = sdk.run_debate()
    assert isinstance(result, DebateResult)
    assert result.verdict.winner in ("dogs", "cats")
    assert len(result.pings) == 2  # 1 round × 2 sides


def test_sdk_get_last_verdict_after_run(tmp_path: Path):
    sdk = _sdk(tmp_path, num_rounds=1)
    sdk.run_debate()
    v = sdk.get_last_verdict()
    assert isinstance(v, Verdict)


def test_sdk_get_last_verdict_reads_disk_when_no_in_memory(tmp_path: Path):
    sdk1 = _sdk(tmp_path, num_rounds=1)
    sdk1.run_debate()
    # Fresh SDK, same results dir — should still find the persisted verdict.
    sdk2 = DebateSDK(
        setup=sdk1.setup, results_dir=tmp_path, provider_factory=_fake_provider_factory()
    )
    v = sdk2.get_last_verdict()
    assert isinstance(v, Verdict)


def test_sdk_get_last_verdict_none_when_empty(tmp_path: Path):
    sdk = DebateSDK(
        setup=_sdk(tmp_path).setup,
        results_dir=tmp_path / "empty",
        provider_factory=_fake_provider_factory(),
    )
    assert sdk.get_last_verdict() is None


def test_sdk_list_past_debates(tmp_path: Path):
    sdk = _sdk(tmp_path, num_rounds=1)
    assert sdk.list_past_debates() == []
    sdk.run_debate()
    files = sdk.list_past_debates()
    assert len(files) == 1
    assert files[0].suffix == ".json"


def test_sdk_get_cost_report_empty_before_run(tmp_path: Path):
    sdk = _sdk(tmp_path)
    assert sdk.get_cost_report() == {}


def test_sdk_passthrough_gatekeeper_default(tmp_path: Path):
    """Default gatekeeper is the passthrough stub — proves the chokepoint
    interface is honored even before Phase 4.1 lands the real one."""
    sdk = _sdk(tmp_path, num_rounds=1)
    assert hasattr(sdk.gatekeeper, "execute")
    # Calling it with a lambda just forwards args.
    assert sdk.gatekeeper.execute(lambda x: x * 2, 21) == 42
