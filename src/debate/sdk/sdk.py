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

from debate.services.agents.cats_agent import CatsAgent
from debate.services.agents.dogs_agent import DogsAgent
from debate.services.agents.judge_agent import JudgeAgent
from debate.services.orchestrator import Orchestrator
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
    ) -> None:
        # Read .env before any provider tries to look up an API key.
        load_env(dotenv_path)
        self.setup = setup if setup is not None else load_setup(setup_path)
        self.gatekeeper = gatekeeper or self._build_gatekeeper(rate_limits_path, logging_path)
        self.results_dir = Path(results_dir)
        self.provider_factory = provider_factory
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
        dogs = DogsAgent(
            provider=self.provider_factory(cfg.models["dogs"].provider),
            gatekeeper=self.gatekeeper,
            model_name=cfg.models["dogs"].name,
        )
        cats = CatsAgent(
            provider=self.provider_factory(cfg.models["cats"].provider),
            gatekeeper=self.gatekeeper,
            model_name=cfg.models["cats"].name,
        )
        judge = JudgeAgent(
            provider=self.provider_factory(cfg.models["judge"].provider),
            gatekeeper=self.gatekeeper,
            model_name=cfg.models["judge"].name,
        )
        orch_kwargs: dict[str, Any] = {
            "topic": topic or cfg.topic,
            "num_rounds": cfg.num_rounds,
            "results_dir": self.results_dir,
            "on_event": on_event,
            "models": cfg.models,
            "pricing": cfg.pricing,
            "cost_report_factory": self.gatekeeper.get_token_summary
            if hasattr(self.gatekeeper, "get_token_summary")
            else None,
        }
        if coin_flip is not None:
            orch_kwargs["coin_flip"] = coin_flip
        orch = Orchestrator(**orch_kwargs)
        self._last_result = orch.run_debate(dogs, cats, judge)
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
        if self._last_result is None:
            return {}
        return dict(self._last_result.cost_report)

    def list_past_debates(self) -> list[Path]:
        if not self.results_dir.exists():
            return []
        return sorted(self.results_dir.glob("debate_*.json"))

    def _latest_result_path(self) -> Path | None:
        debates = self.list_past_debates()
        return debates[-1] if debates else None
