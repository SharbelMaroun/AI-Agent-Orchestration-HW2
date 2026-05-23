"""Shared fixtures for the gatekeeper test files. Not a test module itself
— filename starts with `_` so pytest does not collect it."""

from __future__ import annotations

import logging

from debate.shared.config import (
    BudgetCfg,
    ModelPrice,
    ModelRef,
    RagCfg,
    RateLimitConfig,
    SearchCfg,
    ServiceLimit,
    SetupConfig,
    Timeouts,
)
from debate.shared.gatekeeper import ApiGatekeeper
from debate.shared.schemas import CompletionResponse


class FakeHttpError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def service(**over) -> ServiceLimit:
    base = {
        "requests_per_minute": 60,
        "requests_per_hour": 600,
        "concurrent_max": 5,
        "retry_after_seconds": 1,
        "max_retries": 3,
        "queue_max_depth": 10,
        "retryable_status_codes": [429, 500, 503],
    }
    base.update(over)
    return ServiceLimit(**base)


def rate_cfg(svc: ServiceLimit | None = None, warn: int = 80, hard: int = 100) -> RateLimitConfig:
    return RateLimitConfig(
        version="1.00",
        services={"default": svc or service()},
        budget=BudgetCfg(warning_threshold_pct=warn, hard_limit_pct=hard),
    )


def setup_cfg(budget: float = 5.0) -> SetupConfig:
    return SetupConfig(
        version="1.00",
        topic="t",
        num_rounds=1,
        max_words_per_ping=10,
        budget_usd=budget,
        models={"dogs": ModelRef(provider="anthropic", name="haiku")},
        timeouts=Timeouts(
            agent_response_seconds=10,
            watchdog_heartbeat_seconds=1,
            watchdog_kill_after_seconds=5,
            max_restarts_per_agent=1,
        ),
        rag=RagCfg(enabled=False, k=1, chunk_size=10, embedder="x", persist_dir="x"),
        search=SearchCfg(provider="ddg", max_results=1, timeout_seconds=1),
        pricing={
            "anthropic": {
                "haiku": ModelPrice(input_per_million_usd=1.0, output_per_million_usd=4.0),
            }
        },
    )


def gk(svc=None, budget: float = 5.0, warn: int = 80) -> ApiGatekeeper:
    return ApiGatekeeper(
        rate_config=rate_cfg(svc, warn=warn),
        setup=setup_cfg(budget),
        logger=logging.getLogger("test"),
        cost_logger=None,
        sleep_fn=lambda _s: None,
    )


def resp(
    in_tok: int = 100, out_tok: int = 50, cache_creation: int = 0, cache_read: int = 0
) -> CompletionResponse:
    return CompletionResponse(
        text="hi",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
        model="haiku",
        provider="anthropic",
    )
