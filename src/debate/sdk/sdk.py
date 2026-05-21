"""DebateSDK — sole entry point for the debate system. Phase 3.10."""


class DebateSDK:
    """Public facade. Wires orchestrator + gatekeeper + watchdog + logger. Phase 3.10."""

    def run_debate(self, topic: str | None = None) -> object:
        """Run a full debate end-to-end and return the DebateResult. Phase 3.10."""
        raise NotImplementedError

    def get_last_verdict(self) -> object:
        """Return the most recent Verdict from results/debates/. Phase 3.10."""
        raise NotImplementedError

    def get_cost_report(self) -> object:
        """Aggregate cost across the last run. Phase 3.10."""
        raise NotImplementedError
