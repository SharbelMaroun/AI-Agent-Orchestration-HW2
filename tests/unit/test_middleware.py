"""Unit tests for the gatekeeper middleware chain (debate.shared.middleware)."""

from __future__ import annotations

import logging

from debate.shared.gatekeeper import ApiGatekeeper
from debate.shared.middleware import compose

from ._gatekeeper_fixtures import rate_cfg, resp, setup_cfg


def test_compose_empty_returns_original() -> None:
    def fn(x):
        return x

    assert compose([], fn) is fn  # zero overhead when no middlewares


def test_compose_runs_in_onion_order() -> None:
    order: list[str] = []

    def outer(call_next, *a, **k):
        order.append("outer-before")
        result = call_next(*a, **k)
        order.append("outer-after")
        return result

    def inner(call_next, *a, **k):
        order.append("inner-before")
        result = call_next(*a, **k)
        order.append("inner-after")
        return result

    def base():
        order.append("base")
        return 42

    assert compose([outer, inner], base)() == 42
    assert order == ["outer-before", "inner-before", "base", "inner-after", "outer-after"]


def test_middleware_can_transform_result() -> None:
    def double(call_next, *a, **k):
        return call_next(*a, **k) * 2

    assert compose([double], lambda: 21)() == 42


def _gk_with(middlewares):
    return ApiGatekeeper(
        rate_config=rate_cfg(),
        setup=setup_cfg(),
        logger=logging.getLogger("test"),
        cost_logger=None,
        sleep_fn=lambda _s: None,
        middlewares=middlewares,
    )


def test_gatekeeper_runs_middleware_around_call() -> None:
    seen: list[str] = []

    def spy(call_next, *a, **k):
        seen.append("wrapped")
        return call_next(*a, **k)

    out = _gk_with([spy]).execute(lambda: resp(), service="default")
    assert seen == ["wrapped"]  # middleware ran
    assert out.input_tokens == 100  # underlying call still executed + recorded


def test_gatekeeper_without_middleware_unchanged() -> None:
    out = _gk_with(None).execute(lambda: resp())
    assert out.output_tokens == 50
