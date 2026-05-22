"""DebateAgent — abstract subclass that adds evidence-gathering + JSON
parsing + clash validation on top of BaseAgent. Concrete subclasses
(DogsAgent, CatsAgent) only override the persona-specific bits.

Lives between BaseAgent and the concrete Dogs/Cats agents so that any
machinery shared by both sides has exactly one home — otherwise we drift
into copy/paste between the two persona files (CLAUDE.md §4 OOP rule).

RAG + WebSearch dependencies are typed as `Protocol`s so the agent code
compiles and tests run before Phase 4.4 (web search) and Phase 5.2 (RAG)
land their concrete implementations.
"""

from __future__ import annotations

import json
import re
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, Protocol

from debate.services.agents.base_agent import BaseAgent
from debate.shared.schemas import OpeningBrief, Ping, Side, YourTurn

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class RAGLike(Protocol):
    def retrieve(self, query: str, k: int = 3) -> list[Any]: ...


class SearchLike(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[Any]: ...


class ClashViolationError(ValueError):
    """Ping past round 1 must clash with the opponent's previous ping."""


class PingParseError(ValueError):
    """Raised when the LLM's reply cannot be parsed into a Ping."""


class DebateAgent(BaseAgent):
    """Common Dogs/Cats logic. Side is set by the concrete subclass."""

    side: Side

    def __init__(
        self,
        *args: Any,
        rag: RAGLike | None = None,
        search_tool: SearchLike | None = None,
        rag_k: int = 3,
        search_max_results: int = 5,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.rag = rag
        self.search_tool = search_tool
        self.rag_k = rag_k
        self.search_max_results = search_max_results
        self.opening_brief: OpeningBrief | None = None

    @abstractmethod
    def _build_search_query(self, previous_ping: Ping | None) -> str:
        """Persona-specific query phrasing (e.g., Dogs adds 'study'/'research')."""

    def _collect_evidence(self, query: str) -> dict[str, list]:
        """Gather web-search hits + RAG passages. Either tool may be absent."""
        evidence: dict[str, list] = {"search": [], "rag": []}
        if self.search_tool is not None:
            evidence["search"] = self.search_tool.search(
                query, max_results=self.search_max_results
            )
        if self.rag is not None:
            evidence["rag"] = self.rag.retrieve(query, k=self.rag_k)
        return evidence

    @staticmethod
    def _parse_ping_json(text: str, *, side: Side, round_: int) -> Ping:
        """Extract the first JSON object from the LLM reply and validate it.
        The model is instructed to emit JSON; we still tolerate prose around
        the block so a polite preface doesn't crash the parser."""
        match = _JSON_BLOCK_RE.search(text)
        if not match:
            raise PingParseError("no JSON object found in LLM reply")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise PingParseError(f"invalid JSON in reply: {exc}") from exc
        payload.setdefault("round", round_)
        payload.setdefault("side", side)
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        try:
            return Ping.model_validate(payload)
        except Exception as exc:  # pydantic ValidationError, re-wrapped
            raise PingParseError(f"reply did not match Ping schema: {exc}") from exc

    @staticmethod
    def _validate_clash(ping: Ping, previous_ping: Ping | None) -> None:
        """Round 1 has no opponent ping to clash with. From round 2 onward,
        the new ping must reference the prior round's ping by its round number."""
        if previous_ping is None:
            return
        if ping.refers_to_ping != previous_ping.round:
            raise ClashViolationError(
                f"ping for round {ping.round} must refer to opponent ping "
                f"{previous_ping.round}, got refers_to_ping={ping.refers_to_ping}"
            )

    def _build_user_prompt(
        self,
        previous_ping: Ping | None,
        evidence: dict[str, list],
        round_: int,
    ) -> str:
        prior = "" if previous_ping is None else (
            f"\nOpponent's previous ping (round {previous_ping.round}, "
            f"side {previous_ping.side}):\n{previous_ping.text}\n"
        )
        return (
            f"Round {round_}. You are arguing for the side: {self.side}.\n"
            f"{prior}\n"
            f"Web search evidence: {evidence['search']}\n"
            f"RAG passages: {evidence['rag']}\n\n"
            "Respond with ONE JSON object matching the Ping schema. "
            "If this is round 2+, set `refers_to_ping` to the opponent's round."
        )

    def handle_your_turn(self, envelope: YourTurn) -> Ping:
        query = self._build_search_query(envelope.previous_ping)
        evidence = self._collect_evidence(query)
        prompt = self._build_user_prompt(envelope.previous_ping, evidence, envelope.round)
        response = self.generate(prompt)
        ping = self._parse_ping_json(response.text, side=self.side, round_=envelope.round)
        self._validate_clash(ping, envelope.previous_ping)
        ping.tokens_in = response.input_tokens
        ping.tokens_out = response.output_tokens
        return ping

    def receive(self, envelope: object) -> Ping | None:
        if isinstance(envelope, OpeningBrief):
            self.opening_brief = envelope
            return None
        if isinstance(envelope, YourTurn):
            return self.handle_your_turn(envelope)
        return None
