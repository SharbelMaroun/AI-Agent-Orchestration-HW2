"""Orchestrator — drives the debate loop, manages 3 agent processes.

See docs/PRD.md §3.2 (debate loop) + docs/PLAN.md ADR-001. Phase 3.9.
"""


class Orchestrator:
    """Spawns Dogs/Cats/Judge processes, routes messages, persists result. Phase 3.9."""

    def run_debate(self) -> object:
        """Execute the full debate loop and return a DebateResult. Phase 3.9."""
        raise NotImplementedError
