"""Child-process entry point for debate agents."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from queue import Empty
from typing import Any

from debate.sdk.wiring import speaking_agent_kwargs
from debate.services.agents.cats_agent import CatsAgent
from debate.services.agents.dogs_agent import DogsAgent
from debate.services.agents.judge_agent import JudgeAgent
from debate.shared.config import (
    SetupConfig,
    load_env,
    load_logging,
    load_rate_limits,
)
from debate.shared.gatekeeper import ApiGatekeeper
from debate.shared.llm_provider.base import build_provider
from debate.shared.logger import get_cost_logger, get_logger
from debate.shared.schemas import Heartbeat


def _build_gatekeeper(setup: SetupConfig, rate_path: str, logging_path: str) -> ApiGatekeeper:
    log_cfg = load_logging(logging_path)
    return ApiGatekeeper(
        load_rate_limits(rate_path),
        setup,
        get_logger("gatekeeper", log_cfg),
        get_cost_logger(log_cfg),
    )


def _build_agent(kind: str, setup: SetupConfig, gatekeeper: ApiGatekeeper) -> Any:
    model_ref = setup.models[kind]
    common = {
        "provider": build_provider(model_ref.provider),
        "gatekeeper": gatekeeper,
        "model_name": model_ref.name,
        "request_timeout": setup.timeouts.agent_response_seconds,
    }
    if kind == "dogs":
        return DogsAgent(**common, **speaking_agent_kwargs("dogs", setup, gatekeeper))
    if kind == "cats":
        return CatsAgent(**common, **speaking_agent_kwargs("cats", setup, gatekeeper))
    return JudgeAgent(**common)


def _heartbeat_loop(kind: str, heartbeat_q: Any, interval: float, stop: threading.Event) -> None:
    """Daemon-thread heartbeat — keeps the watchdog happy even while the
    main loop is inside a long `agent.receive(...)` call (web search +
    embedder cold-start + LLM round-trip can easily exceed the kill timeout)."""
    while not stop.is_set():
        heartbeat_q.put(Heartbeat(agent_id=kind, timestamp=datetime.now(timezone.utc)))
        stop.wait(interval)


def agent_process_main(
    kind: str,
    setup_data: dict,
    rate_path: str,
    logging_path: str,
    inbox: Any,
    outbox: Any,
    heartbeat_q: Any,
    dotenv_path: str = ".env",
) -> None:
    load_env(dotenv_path)
    setup = SetupConfig.model_validate(setup_data)
    gatekeeper = _build_gatekeeper(setup, rate_path, logging_path)
    agent = _build_agent(kind, setup, gatekeeper)
    heartbeat_seconds = setup.timeouts.watchdog_heartbeat_seconds
    stop_heartbeat = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(kind, heartbeat_q, heartbeat_seconds, stop_heartbeat),
        daemon=True,
    )
    hb_thread.start()
    try:
        while True:
            try:
                envelope = inbox.get(timeout=heartbeat_seconds)
            except Empty:
                continue
            if envelope is None:
                outbox.put(
                    {"agent": kind, "kind": "cost", "payload": gatekeeper.get_token_summary()}
                )
                return
            try:
                result = agent.receive(envelope)
            except Exception as exc:
                outbox.put({"agent": kind, "kind": "error", "payload": repr(exc)})
                continue
            if result is not None:
                outbox.put({"agent": kind, "kind": "result", "payload": result})
    finally:
        stop_heartbeat.set()
