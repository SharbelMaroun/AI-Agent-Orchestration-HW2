"""CatsAgent — pathos/Socratic style. side="cats". See docs/PRD_cats.md. Phase 3.7."""

from debate.services.agents.base_agent import BaseAgent


class CatsAgent(BaseAgent):
    """Argues cats are the better pet using imagery + literary references. Phase 3.7."""

    def receive(self, envelope: object) -> None:
        """Phase 3.7."""
        raise NotImplementedError
