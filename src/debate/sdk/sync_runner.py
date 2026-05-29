"""In-process debate runner kept for fast tests and direct debugging."""

from __future__ import annotations

from typing import Any

from debate.services._orchestrator_helpers import make_rules
from debate.services.agents.cats_agent import CatsAgent
from debate.services.agents.dogs_agent import DogsAgent
from debate.services.agents.judge_agent import JudgeAgent
from debate.services.orchestrator import Orchestrator
from debate.shared.config import SetupConfig

from .wiring import speaking_agent_kwargs


def run_sync_debate(
    *,
    setup: SetupConfig,
    gatekeeper: Any,
    provider_factory: Any,
    results_dir: Any,
    topic: str | None,
    on_event: Any,
    coin_flip: Any,
    wire_tools: bool,
) -> Any:
    request_timeout = setup.timeouts.agent_response_seconds
    dogs = DogsAgent(
        provider=provider_factory(setup.models["dogs"].provider),
        gatekeeper=gatekeeper,
        model_name=setup.models["dogs"].name,
        request_timeout=request_timeout,
        **_tool_kwargs("dogs", setup, gatekeeper, wire_tools),
    )
    cats = CatsAgent(
        provider=provider_factory(setup.models["cats"].provider),
        gatekeeper=gatekeeper,
        model_name=setup.models["cats"].name,
        request_timeout=request_timeout,
        **_tool_kwargs("cats", setup, gatekeeper, wire_tools),
    )
    judge = JudgeAgent(
        provider=provider_factory(setup.models["judge"].provider),
        gatekeeper=gatekeeper,
        model_name=setup.models["judge"].name,
        request_timeout=request_timeout,
    )
    kwargs = {
        "topic": topic or setup.topic,
        "num_rounds": setup.num_rounds,
        "rules": make_rules(setup.max_words_per_ping),
        "results_dir": results_dir,
        "on_event": on_event,
        "models": setup.models,
        "pricing": setup.pricing,
        "cost_report_factory": gatekeeper.get_token_summary
        if hasattr(gatekeeper, "get_token_summary")
        else None,
    }
    if coin_flip is not None:
        kwargs["coin_flip"] = coin_flip
    return Orchestrator(**kwargs).run_debate(dogs, cats, judge)


def _tool_kwargs(side: str, setup: SetupConfig, gatekeeper: Any, wire_tools: bool) -> dict:
    if not wire_tools:
        return {}
    return speaking_agent_kwargs(side, setup, gatekeeper)
