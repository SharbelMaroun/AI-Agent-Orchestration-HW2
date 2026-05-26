"""DebateSDK — sole entry point per CLAUDE.md §4 (no business logic in CLI/GUI).

The SDK wires concrete agents to the Orchestrator and builds the real
ApiGatekeeper by default, so normal CLI runs get rate limiting, retries,
and token/cost tracking. Construction-time dependency injection
(providers, gatekeeper, results_dir) lets tests swap any dependency
without touching the SDK body.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from debate.sdk.sync_runner import run_sync_debate
from debate.services.process_orchestrator import ProcessOrchestrator
from debate.shared.config import (
    SetupConfig,
    load_env,
    load_logging,
    load_rate_limits,
    load_setup,
)
from debate.shared.gatekeeper import ApiGatekeeper
from debate.shared.llm_provider.base import build_provider
from debate.shared.logger import get_cost_logger, get_logger
from debate.shared.schemas import DebateResult, Verdict


class _PassthroughGatekeeper:
    """Test helper for callers that want unmetered local execution."""

    def execute(
        self, api_call: Callable, *args: Any, service: str = "default", **kwargs: Any
    ) -> Any:
        del service  # accepted for protocol compatibility
        return api_call(*args, **kwargs)


class DebateSDK:
    """Public facade. The CLI and any future UI talk only to this class."""

    def __init__(
        self,
        setup: SetupConfig | None = None,
        setup_path: str | Path = "config/setup.json",
        rate_limits_path: str | Path = "config/rate_limits.json",
        logging_path: str | Path = "config/logging_config.json",
        gatekeeper: Any | None = None,
        results_dir: Path | str = "results/debates",
        provider_factory: Callable[[str], Any] = build_provider,
        dotenv_path: str | Path = ".env",
        wire_tools: bool = True,
        use_processes: bool = True,
    ) -> None:
        # Read .env before any provider tries to look up an API key.
        load_env(dotenv_path)
        self.setup = setup or load_setup(setup_path)
        self.gatekeeper = gatekeeper or self._build_gatekeeper(rate_limits_path, logging_path)
        self.rate_limits_path = rate_limits_path
        self.logging_path = logging_path
        self.results_dir = Path(results_dir)
        self.provider_factory = provider_factory
        self.wire_tools = wire_tools
        self.use_processes = use_processes
        self._last_result: DebateResult | None = None

    def _build_gatekeeper(
        self,
        rate_limits_path: str | Path,
        logging_path: str | Path,
    ) -> ApiGatekeeper:
        log_cfg = load_logging(logging_path)
        logger = get_logger("gatekeeper", log_cfg)
        return ApiGatekeeper(
            load_rate_limits(rate_limits_path),
            self.setup,
            logger,
            get_cost_logger(log_cfg),
        )

    def run_debate(
        self,
        topic: str | None = None,
        on_event: Callable[[str, Any], None] | None = None,
        coin_flip: Callable[[], int] | None = None,
    ) -> DebateResult:
        cfg = self.setup
        if hasattr(self.gatekeeper, "reset_costs"):
            self.gatekeeper.reset_costs()
        if self.use_processes:
            kwargs = {
                "results_dir": self.results_dir,
                "rate_limits_path": self.rate_limits_path,
                "logging_path": self.logging_path,
                "on_event": on_event,
            }
            if coin_flip is not None:
                kwargs["coin_flip"] = coin_flip
            orch = ProcessOrchestrator(self.setup, **kwargs)
            self._last_result = orch.run_debate()
            return self._last_result
        self._last_result = run_sync_debate(
            setup=cfg,
            gatekeeper=self.gatekeeper,
            provider_factory=self.provider_factory,
            results_dir=self.results_dir,
            topic=topic,
            on_event=on_event,
            coin_flip=coin_flip,
            wire_tools=self.wire_tools,
        )
        return self._last_result

    def get_last_verdict(self) -> Verdict | None:
        if self._last_result is not None:
            return self._last_result.verdict
        latest = self._latest_result_path()
        if latest is None:
            return None
        payload = json.loads(latest.read_text(encoding="utf-8"))
        return Verdict.model_validate(payload["verdict"])

    def get_cost_report(self) -> dict:
        if self._last_result is not None:
            return dict(self._last_result.cost_report)
        fallback: dict = {}
        for path in reversed(self.list_past_debates()):
            payload = json.loads(path.read_text(encoding="utf-8"))
            report = dict(payload.get("cost_report") or {})
            if report and not fallback:
                fallback = report
            if report.get("by_model"):
                return report
        return fallback

    def list_past_debates(self) -> list[Path]:
        if not self.results_dir.exists():
            return []
        return sorted(self.results_dir.glob("debate_*.json"))

    def _latest_result_path(self) -> Path | None:
        debates = self.list_past_debates()
        return debates[-1] if debates else None
