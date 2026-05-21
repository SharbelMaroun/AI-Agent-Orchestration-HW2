"""DogsAgent — logos/ethos style. side="dogs". See docs/PRD_dogs.md. Phase 3.6."""

from debate.services.agents.base_agent import BaseAgent


class DogsAgent(BaseAgent):
    """Argues dogs are the better pet using studies + authority. Phase 3.6."""

    def receive(self, envelope: object) -> None:
        """Phase 3.6."""
        raise NotImplementedError
