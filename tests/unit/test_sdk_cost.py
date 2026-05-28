"""DebateSDK cost-report + gatekeeper tests (Phase 3.10 / Phase 8 evidence).

Core run/verdict/list tests live in `test_sdk.py`. Shared helpers in `_sdk_fixtures.py`.
"""

from __future__ import annotations

from pathlib import Path

from debate.sdk.sdk import DebateSDK
from debate.shared.gatekeeper import ApiGatekeeper

from ._sdk_fixtures import build_sdk, fake_provider_factory


def test_sdk_get_cost_report_empty_before_run(tmp_path: Path):
    sdk = build_sdk(tmp_path)
    assert sdk.get_cost_report() == {}


def test_sdk_get_cost_report_reads_disk_when_no_in_memory(tmp_path: Path):
    sdk1 = build_sdk(tmp_path, num_rounds=1)
    expected = sdk1.run_debate().cost_report
    sdk2 = DebateSDK(
        setup=sdk1.setup,
        results_dir=tmp_path,
        provider_factory=fake_provider_factory(),
        wire_tools=False,
        use_processes=False,
    )
    assert sdk2.get_cost_report() == expected


def test_sdk_get_cost_report_skips_empty_latest_file(tmp_path: Path):
    sdk1 = build_sdk(tmp_path, num_rounds=1)
    expected = sdk1.run_debate().cost_report
    (tmp_path / "debate_99999999T999999.json").write_text(
        '{"cost_report":{"total_usd":0.0,"by_model":{},"cache_read_pct":0.0},'
        '"verdict":{"winner":"dogs","dogs_total":1,"cats_total":0,"margin":1,'
        '"written_rationale":"x"}}',
        encoding="utf-8",
    )
    sdk2 = DebateSDK(
        setup=sdk1.setup,
        results_dir=tmp_path,
        provider_factory=fake_provider_factory(),
        wire_tools=False,
        use_processes=False,
    )
    assert sdk2.get_cost_report() == expected


def test_sdk_real_gatekeeper_default(tmp_path: Path):
    """Default gatekeeper is the real ApiGatekeeper — proves the chokepoint
    interface is honored by the production gatekeeper."""
    sdk = build_sdk(tmp_path, num_rounds=1)
    assert isinstance(sdk.gatekeeper, ApiGatekeeper)


def test_sdk_persists_gatekeeper_cost_report_with_judge_calls(tmp_path: Path):
    sdk = build_sdk(tmp_path, num_rounds=1)
    result = sdk.run_debate()
    report = result.cost_report
    assert report["total_usd"] > 0
    # All three agents run on gpt-4o-mini. We briefly tried gpt-4o for the judge
    # on 2026-05-28 (it closed the logos gap in the rebalance experiment — see
    # debate_20260528T180117.json) but reverted for cost + speed and kept the
    # finding as a documented one-shot fairness experiment.
    total_input = sum(m["input_tokens"] for m in report["by_model"].values())
    assert total_input == 25
    assert "openai/gpt-4o-mini" in report["by_model"]
