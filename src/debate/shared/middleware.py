"""Middleware chain for the gatekeeper — a documented extension point.

Lets consumers wrap every gatekept API call with cross-cutting concerns
(logging, timing, metrics, auth, extra sanitization) *without* modifying
`ApiGatekeeper.execute` (CLAUDE.md §19: middleware / API-first design).

A middleware is a callable ``mw(call_next, *args, **kwargs)``: it may do work
before and after, then returns ``call_next(*args, **kwargs)``. Middlewares
compose as an onion — the first in the list is the outermost wrapper.

Example::

    def timing(call_next, *args, **kwargs):
        start = time.monotonic()
        try:
            return call_next(*args, **kwargs)
        finally:
            log.info("call took %.3fs", time.monotonic() - start)

    gatekeeper = ApiGatekeeper(..., middlewares=[timing])
"""

from __future__ import annotations

from collections.abc import Callable
from functools import reduce
from typing import Any

# A middleware receives the next callable in the chain plus the call's args.
Middleware = Callable[..., Any]


def compose(middlewares: list[Middleware], api_call: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap ``api_call`` with ``middlewares`` (index 0 = outermost).

    Returns a callable with the same ``(*args, **kwargs)`` signature as
    ``api_call``. An empty list returns ``api_call`` unchanged (zero overhead).
    """

    def _wrap(next_call: Callable[..., Any], mw: Middleware) -> Callable[..., Any]:
        def _chained(*args: Any, **kwargs: Any) -> Any:
            return mw(next_call, *args, **kwargs)

        return _chained

    return reduce(_wrap, reversed(middlewares), api_call)
