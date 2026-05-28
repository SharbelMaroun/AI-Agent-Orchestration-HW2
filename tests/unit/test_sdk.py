"""DebateSDK core tests — run, last-verdict, list-past-debates (Phase 3.10).

Cost-report tests live in `test_sdk_cost.py`. Shared helpers in `_sdk_fixtures.py`.
"""

from __future__ import annotations

from pathlib import Path

from debate.sdk.sdk import DebateSDK
from debate.shared.schemas import DebateResult, Verdict

from ._sdk_fixtures import build_sdk, fake_provider_factory


def test_sdk_run_debate_returns_result(tmp_path: Path):
    sdk = build_sdk(tmp_path, num_rounds=1)
    result = sdk.run_debate()
    assert isinstance(result, DebateResult)
    assert result.verdict.winner in ("dogs", "cats")
    assert len(result.pings) == 2  # 1 round × 2 sides


def test_sdk_get_last_verdict_after_run(tmp_path: Path):
    sdk = build_sdk(tmp_path, num_rounds=1)
    sdk.run_debate()
    v = sdk.get_last_verdict()
    assert isinstance(v, Verdict)


def test_sdk_get_last_verdict_reads_disk_when_no_in_memory(tmp_path: Path):
    sdk1 = build_sdk(tmp_path, num_rounds=1)
    sdk1.run_debate()
    sdk2 = DebateSDK(
        setup=sdk1.setup,
        results_dir=tmp_path,
        provider_factory=fake_provider_factory(),
        wire_tools=False,
        use_processes=False,
    )
    v = sdk2.get_last_verdict()
    assert isinstance(v, Verdict)


def test_sdk_get_last_verdict_none_when_empty(tmp_path: Path):
    sdk = DebateSDK(
        setup=build_sdk(tmp_path).setup,
        results_dir=tmp_path / "empty",
        provider_factory=fake_provider_factory(),
        wire_tools=False,
        use_processes=False,
    )
    assert sdk.get_last_verdict() is None


def test_sdk_list_past_debates(tmp_path: Path):
    sdk = build_sdk(tmp_path, num_rounds=1)
    assert sdk.list_past_debates() == []
    sdk.run_debate()
    files = sdk.list_past_debates()
    assert len(files) == 1
    assert files[0].suffix == ".json"
