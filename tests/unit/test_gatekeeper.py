"""Gatekeeper core: happy path, cost recording, retry/failure routing.

Budget + queue + concurrency tests live in
`test_gatekeeper_budget_and_queue.py` — split for the 150-LOC test cap."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from debate.shared.gatekeeper import ApiCallFailedError, ApiGatekeeper
from tests.unit._gatekeeper_fixtures import (
    FakeHttpError,
    gk,
    rate_cfg,
    resp,
    service,
    setup_cfg,
)


def test_execute_returns_result() -> None:
    g = gk()
    out = g.execute(lambda: resp())
    assert out.text == "hi"


def test_execute_records_tokens_and_cost() -> None:
    g = gk(budget=1000)
    g.execute(lambda: resp(in_tok=1_000_000, out_tok=1_000_000))
    summary = g.get_token_summary()
    assert summary["by_model"]["anthropic/haiku"]["input_tokens"] == 1_000_000
    assert abs(summary["total_usd"] - 5.0) < 1e-9


def test_execute_records_cache_tokens_separately() -> None:
    g = gk()
    g.execute(lambda: resp(cache_creation=500, cache_read=200))
    entry = g.get_token_summary()["by_model"]["anthropic/haiku"]
    assert entry["cache_creation_tokens"] == 500
    assert entry["cache_read_tokens"] == 200


def test_execute_skips_recording_for_non_completion() -> None:
    g = gk()
    g.execute(lambda: {"results": ["a", "b"]})
    assert g.get_token_summary()["total_usd"] == 0.0


def test_retries_on_retryable_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeHttpError(429)
        return resp()

    g = gk(svc=service(max_retries=3, retry_after_seconds=0))
    assert g.execute(flaky).text == "hi"
    assert calls["n"] == 3


def test_max_retries_raises_api_call_failed() -> None:
    g = gk(svc=service(max_retries=2, retry_after_seconds=0))
    with pytest.raises(ApiCallFailedError):
        g.execute(lambda: (_ for _ in ()).throw(FakeHttpError(503)))


def test_non_retryable_exception_propagates() -> None:
    g = gk()

    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        g.execute(boom)


def test_timeout_is_retried() -> None:
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("slow")
        return resp()

    g = gk(svc=service(max_retries=2, retry_after_seconds=0))
    g.execute(flaky)
    assert calls["n"] == 2


def test_unknown_service_falls_back_to_default() -> None:
    g = gk()
    g.execute(lambda: resp(), service="nonexistent")
    assert g.get_queue_status("nonexistent").service == "nonexistent"


def test_cost_logger_called_when_provided() -> None:
    cost_log = MagicMock()
    g = ApiGatekeeper(
        rate_config=rate_cfg(),
        setup=setup_cfg(),
        logger=logging.getLogger("test"),
        cost_logger=cost_log,
        sleep_fn=lambda _s: None,
    )
    g.execute(lambda: resp())
    assert cost_log.info.called
