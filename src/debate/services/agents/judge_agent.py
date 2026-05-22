"""JudgeAgent — scores every ping on a 5-dimension rubric and declares a
non-tie winner. No RAG, no web search (intentionally not a fact-checker).
See docs/PRD_judge.md."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from debate.services.agents.base_agent import BaseAgent
from debate.shared.schemas import Ping, Score, Side, Verdict
from debate.shared.skill_loader import load_skill

DEFAULT_SKILL_PATH = Path("skills/judge")
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_CONCESSION_PHRASES = (
    "good point", "fair enough", "i agree", "you're right",
    "i concede", "valid point", "you make a good",
)


class FinalizeRequest:
    """Sentinel envelope: 'all rounds delivered, now give the verdict'."""

    def __init__(self, pings: list[Ping]) -> None:
        self.pings = pings


class JudgeAgent(BaseAgent):
    """Scores every ping, then synthesizes a verdict at the end."""

    def __init__(
        self,
        *args: Any,
        system_prompt: str | None = None,
        skill_path: Path | str = DEFAULT_SKILL_PATH,
        **kwargs: Any,
    ) -> None:
        if system_prompt is None:
            system_prompt = load_skill(skill_path)
        kwargs["system_prompt"] = system_prompt
        kwargs.setdefault("agent_id", "judge")
        super().__init__(*args, **kwargs)
        self.scores: list[Score] = []

    def score_ping(self, ping: Ping) -> Score:
        prompt = (
            f"Score this ping (round {ping.round}, side {ping.side}):\n\n"
            f"{ping.text}\n\n"
            "Reply with ONE JSON object matching the per-ping rubric schema."
        )
        response = self.generate(prompt)
        payload = self._extract_json(response.text)
        if self._is_concession(ping.text):
            payload["clash"] = 0
        payload.update({"ping_round": ping.round, "side": ping.side})
        score = Score.model_validate(payload)
        self.scores.append(score)
        return score

    def decide_winner(self, pings: list[Ping]) -> Verdict:
        dogs_total = sum(self._total(s) for s in self.scores if s.side == "dogs")
        cats_total = sum(self._total(s) for s in self.scores if s.side == "cats")
        prompt = (
            f"Final scores — dogs: {dogs_total}, cats: {cats_total}.\n"
            f"Score detail: {[s.model_dump() for s in self.scores]}\n"
            "Deliver the verdict as ONE JSON object."
        )
        response = self.generate(prompt)
        payload = self._extract_json(response.text)
        payload["dogs_total"] = dogs_total
        payload["cats_total"] = cats_total
        payload["margin"] = abs(dogs_total - cats_total)
        if dogs_total == cats_total:
            payload["winner"] = self._tie_break()
            payload["margin"] = 0
        payload.setdefault("key_points_dogs", self._extract_key_points(pings, "dogs"))
        payload.setdefault("key_points_cats", self._extract_key_points(pings, "cats"))
        return Verdict.model_validate(payload)

    def receive(self, envelope: object) -> Score | Verdict | None:
        if isinstance(envelope, Ping):
            return self.score_ping(envelope)
        if isinstance(envelope, FinalizeRequest):
            return self.decide_winner(envelope.pings)
        return None

    def _tie_break(self) -> Side:
        """Per PRD §6: highest cumulative clash, then pathos, then dogs by
        default convention (Dogs opens, so the tie-break tie is assigned to
        the opener — not an editorial preference)."""
        dogs_clash = sum(s.clash for s in self.scores if s.side == "dogs")
        cats_clash = sum(s.clash for s in self.scores if s.side == "cats")
        if dogs_clash != cats_clash:
            return "dogs" if dogs_clash > cats_clash else "cats"
        dogs_pathos = sum(s.pathos for s in self.scores if s.side == "dogs")
        cats_pathos = sum(s.pathos for s in self.scores if s.side == "cats")
        if dogs_pathos != cats_pathos:
            return "dogs" if dogs_pathos > cats_pathos else "cats"
        return "dogs"

    @staticmethod
    def _total(score: Score) -> int:
        return score.structure + score.logos + score.pathos + score.ethos + score.clash

    @staticmethod
    def _is_concession(text: str) -> bool:
        low = text.lower()
        return any(phrase in low for phrase in _CONCESSION_PHRASES)

    @staticmethod
    def _detect_collusion(recent_pings: list[Ping], window: int = 3) -> bool:
        """Three consecutive concessions = collusion warning."""
        if len(recent_pings) < window:
            return False
        tail = recent_pings[-window:]
        return all(JudgeAgent._is_concession(p.text) for p in tail)

    @staticmethod
    def _extract_key_points(pings: list[Ping], side: Side, k: int = 3) -> list[str]:
        """Fallback if the LLM verdict didn't supply them — take the first
        sentence of the top-k pings for the side."""
        out: list[str] = []
        for p in pings:
            if p.side != side:
                continue
            first = p.text.split(".")[0].strip()
            if first:
                out.append(first[:80])
            if len(out) >= k:
                break
        return out

    @staticmethod
    def _extract_json(text: str) -> dict:
        match = _JSON_BLOCK_RE.search(text)
        if not match:
            raise ValueError("no JSON in judge reply")
        return json.loads(match.group(0))
