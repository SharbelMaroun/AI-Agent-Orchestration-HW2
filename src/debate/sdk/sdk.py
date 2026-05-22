"""DebateSDK — sole entry point per CLAUDE.md §4 (no business logic in CLI/GUI).

The SDK wires concrete agents to the Orchestrator. The Gatekeeper is the
real Phase 4.1 class once it exists; until then a passthrough stand-in is
injected so the SDK is usable by the CLI for end-to-end smoke runs.
Construction-time dependency injection (providers, gatekeeper, results_dir)
lets tests swap any of these without touching the SDK body.
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
from debate.shared.config import SetupConfig, load_setup
from debate.shared.llm_provider.base import build_provider
from debate.shared.schemas import DebateResult, Verdict


class _PassthroughGatekeeper:
    """Stub until Phase 4.1 lands the real ApiGatekeeper. Honors the
    Protocol `BaseAgent` expects so it drops in without agent changes."""

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
        gatekeeper: Any | None = None,
        results_dir: Path | str = "results/debates",
        provider_factory: Callable[[str], Any] = build_provider,
    ) -> None:
        self.setup = setup if setup is not None else load_setup(setup_path)
        self.gatekeeper = gatekeeper or _PassthroughGatekeeper()
        self.results_dir = Path(results_dir)
        self.provider_factory = provider_factory
        self._last_result: DebateResult | None = None

    def run_debate(self, topic: str | None = None) -> DebateResult:
        cfg = self.setup
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
        orch = Orchestrator(
            topic=topic or cfg.topic,
            num_rounds=cfg.num_rounds,
            results_dir=self.results_dir,
        )
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
