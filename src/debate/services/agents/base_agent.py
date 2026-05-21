"""BaseAgent — abstract parent for all three agents. Phase 3.4.

Holds: id, system_prompt, LLMProvider, gatekeeper, history, logger.
See docs/PLAN.md §4 class diagram.
"""

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Common machinery: history management, gatekeeper-wrapped LLM calls. Phase 3.4."""

    def generate(self, user_message: str) -> object:
        """Append to history, call provider via gatekeeper, return CompletionResponse. Phase 3.4."""
        raise NotImplementedError

    @abstractmethod
    def receive(self, envelope: object) -> None:
        """Process an incoming JSON envelope. Subclasses dispatch by MessageType."""

    def run(self, inbox_queue: object, outbox_queue: object) -> None:
        """Main process loop. Phase 3.4."""
        raise NotImplementedError
