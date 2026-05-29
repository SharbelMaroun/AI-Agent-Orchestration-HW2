"""BaseAgent — abstract parent for all three agents. See docs/PLAN.md §4.

Each agent process owns:
  - a system prompt (string, persona)
  - an `LLMProvider` instance (vendor SDK wrapper)
  - a `gatekeeper.execute(...)` callable (rate limits + retries + cost tracking)
  - a private `history: list[ChatMessage]` (the model is stateless — we resend)
  - a logger

The split between provider and gatekeeper is the key invariant: the agent
never calls `provider.complete(...)` directly. It always goes through
`gatekeeper.execute(provider.complete, ...)` so every API call is metered.
This is the "single chokepoint" rule from CLAUDE.md §5.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol

from debate.shared.llm_provider.base import LLMProvider
from debate.shared.schemas import ChatMessage, CompletionResponse, Heartbeat


class GatekeeperLike(Protocol):
    """Structural type the agent depends on. Real Gatekeeper lands in Phase 4.1."""

    def execute(self, api_call, *args, service: str = "default", **kwargs) -> Any: ...


class BaseAgent(ABC):
    """Holds history; routes generation through the gatekeeper."""

    def __init__(
        self,
        agent_id: str,
        system_prompt: str,
        provider: LLMProvider,
        gatekeeper: GatekeeperLike,
        model_name: str,
        logger: logging.Logger | None = None,
        max_tokens: int = 1024,
        request_timeout: float | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.provider = provider
        self.gatekeeper = gatekeeper
        self.model_name = model_name
        self.max_tokens = max_tokens
        # Per-LLM-call wall-clock limit (seconds). Wired from
        # setup.timeouts.agent_response_seconds; kept below the watchdog's
        # kill_after so the call times out before the process is killed.
        self.request_timeout = request_timeout
        self.logger = logger or logging.getLogger(f"agent.{agent_id}")
        self.history: list[ChatMessage] = []

    def _append_user(self, content: str) -> None:
        self.history.append(ChatMessage(role="user", content=content))

    def _append_assistant(self, content: str) -> None:
        self.history.append(ChatMessage(role="assistant", content=content))

    def generate(self, user_message: str) -> CompletionResponse:
        """Append the user message, call the provider via the gatekeeper, and
        record the assistant reply. Returns the normalized response so callers
        can read token counts for cost reporting."""
        self._append_user(user_message)
        response: CompletionResponse = self.gatekeeper.execute(
            self.provider.complete,
            system=self.system_prompt,
            messages=list(self.history),
            model=self.model_name,
            max_tokens=self.max_tokens,
            timeout=self.request_timeout,
            service="default",
        )
        self._append_assistant(response.text)
        self.logger.debug(
            "agent=%s tokens_in=%d tokens_out=%d",
            self.agent_id,
            response.input_tokens,
            response.output_tokens,
        )
        return response

    @abstractmethod
    def receive(self, envelope: object) -> object | None:
        """Dispatch one incoming envelope. Subclasses route by `envelope.type`."""

    def heartbeat(self, out_queue: Any, timestamp) -> None:
        """Emit a HEARTBEAT envelope so the Watchdog knows we're alive."""
        out_queue.put(Heartbeat(agent_id=self.agent_id, timestamp=timestamp))

    def run(self, inbox: Any, outbox: Any) -> None:
        """Process main loop: pull envelope → receive → forward result. Calling
        code is responsible for sending a sentinel `None` to terminate cleanly."""
        while True:
            envelope = inbox.get()
            if envelope is None:
                self.logger.info("agent=%s received shutdown sentinel", self.agent_id)
                return
            try:
                result = self.receive(envelope)
            except Exception:
                self.logger.exception("agent=%s failed handling envelope", self.agent_id)
                raise
            if result is not None:
                outbox.put(result)
