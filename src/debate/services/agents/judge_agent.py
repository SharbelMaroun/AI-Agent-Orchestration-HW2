"""JudgeAgent — 5-dim rubric, no RAG, no web search. See docs/PRD_judge.md. Phase 3.8."""

from debate.services.agents.base_agent import BaseAgent


class JudgeAgent(BaseAgent):
    """Scores every ping and declares a winner (no ties). Phase 3.8."""

    def score_ping(self, ping: object) -> object:
        """Return a Score for one ping. Phase 3.8."""
        raise NotImplementedError

    def decide_winner(self, scores: list, pings: list) -> object:
        """Return a Verdict with winner + rationale + key points. Phase 3.8."""
        raise NotImplementedError

    def receive(self, envelope: object) -> None:
        """Phase 3.8."""
        raise NotImplementedError
