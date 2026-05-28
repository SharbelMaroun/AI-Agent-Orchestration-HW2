"""DebateAgent — abstract subclass adding evidence-gathering + JSON parsing
+ clash validation on top of BaseAgent. Pure helpers in `_debate_agent_helpers.py`."""

from __future__ import annotations

from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Protocol

from debate.services.agents._debate_agent_helpers import (
    ClashViolationError,  # noqa: F401  (re-exported for callers)
    PingParseError,  # noqa: F401
    build_user_prompt,
    parse_ping_json,
    sanitize_hits,
    sanitize_passages,
    validate_clash,
)
from debate.services.agents.base_agent import BaseAgent
from debate.services.research import build_research_cards
from debate.shared.schemas import OpeningBrief, Ping, Side, YourTurn
from debate.shared.security import SecuritySanitizer


class RAGLike(Protocol):
    def retrieve(self, query: str, k: int = 3) -> list[Any]: ...


class SearchLike(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[Any]: ...


class DebateAgent(BaseAgent):
    """Common Dogs/Cats logic. Side is set by the concrete subclass."""

    side: Side

    # Static helpers re-exposed as class attributes so existing call sites
    # `DebateAgent._parse_ping_json(...)` / `_validate_clash(...)` in tests
    # keep working without import changes.
    _parse_ping_json = staticmethod(parse_ping_json)
    _validate_clash = staticmethod(validate_clash)

    def __init__(
        self,
        *args: Any,
        rag: RAGLike | None = None,
        search_tool: SearchLike | None = None,
        rag_k: int = 3,
        search_max_results: int = 5,
        sanitizer: SecuritySanitizer | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.rag = rag
        self.search_tool = search_tool
        self.rag_k = rag_k
        self.search_max_results = search_max_results
        self.sanitizer = sanitizer or SecuritySanitizer()
        self.opening_brief: OpeningBrief | None = None

    @abstractmethod
    def _build_search_query(self, previous_ping: Ping | None) -> str:
        """Persona-specific query phrasing (e.g., Dogs adds 'study'/'research')."""

    def _collect_evidence(self, query: str) -> dict[str, list]:
        """Gather web-search hits + RAG passages in parallel; all untrusted text is
        sanitized before it can reach the agent's prompt (see security.py)."""
        evidence: dict[str, list] = {"search": [], "rag": [], "research_cards": []}

        def _search() -> list:
            if self.search_tool is None:
                return []
            hits = self.search_tool.search(query, max_results=self.search_max_results)
            return sanitize_hits(hits, self.sanitizer)

        def _rag() -> list:
            if self.rag is None:
                return []
            passages = self.rag.retrieve(query, k=self.rag_k)
            return sanitize_passages(passages, self.sanitizer)

        with ThreadPoolExecutor(max_workers=2) as ex:
            search_fut = ex.submit(_search)
            rag_fut = ex.submit(_rag)
            evidence["search"] = search_fut.result()
            evidence["rag"] = rag_fut.result()
        evidence["research_cards"] = [
            card.model_dump() for card in build_research_cards(self.side, evidence)
        ]
        return evidence

    def _build_user_prompt(
        self,
        previous_ping: Ping | None,
        evidence: dict[str, list],
        round_: int,
    ) -> str:
        return build_user_prompt(self.side, previous_ping, evidence, round_)

    def handle_your_turn(self, envelope: YourTurn) -> Ping:
        query = self._build_search_query(envelope.previous_ping)
        evidence = self._collect_evidence(query)
        prompt = self._build_user_prompt(envelope.previous_ping, evidence, envelope.round)
        response = self.generate(prompt)
        try:
            ping = parse_ping_json(response.text, side=self.side, round_=envelope.round)
        except PingParseError:
            repair = self.generate(self._repair_prompt(response.text, envelope.round))
            response = response.model_copy(
                update={
                    "text": repair.text,
                    "input_tokens": response.input_tokens + repair.input_tokens,
                    "output_tokens": response.output_tokens + repair.output_tokens,
                }
            )
            try:
                ping = parse_ping_json(response.text, side=self.side, round_=envelope.round)
            except PingParseError:
                ping = self._fallback_ping(response.text, envelope.round, envelope.previous_ping)
        # Defensive: smaller models sometimes omit `refers_to_ping` OR return a
        # wrong round number (off-by-one hallucinations seen in late rounds).
        # The structural field is unambiguous from envelope context — auto-fix
        # both shapes to envelope.previous_ping.round. The Judge's `clash`
        # dimension separately scores rhetorical engagement, so this only
        # corrects the bookkeeping, not the substantive clash quality.
        if (
            envelope.previous_ping is not None
            and ping.refers_to_ping != envelope.previous_ping.round
        ):
            ping = ping.model_copy(update={"refers_to_ping": envelope.previous_ping.round})
        validate_clash(ping, envelope.previous_ping)
        ping.tokens_in = response.input_tokens
        ping.tokens_out = response.output_tokens
        return ping

    def _repair_prompt(self, bad_reply: str, round_: int) -> str:
        return (
            "Your previous reply was not valid JSON. Convert it into exactly one JSON object "
            f'for round {round_}: {{"text":"<argument>","citations":[],"refers_to_ping":null}}. '
            f"No prose outside JSON. Previous reply:\n{bad_reply}"
        )

    def _fallback_ping(
        self,
        text: str,
        round_: int,
        previous_ping: Ping | None,
    ) -> Ping:
        clean = text.strip() or "The model returned an empty non-JSON argument."
        return Ping(
            round=round_,
            side=self.side,
            text=clean,
            citations=[],
            refers_to_ping=previous_ping.round if previous_ping is not None else None,
            timestamp=datetime.now(timezone.utc),
        )

    def receive(self, envelope: object) -> Ping | None:
        if isinstance(envelope, OpeningBrief):
            self.opening_brief = envelope
            return None
        if isinstance(envelope, YourTurn):
            return self.handle_your_turn(envelope)
        return None
