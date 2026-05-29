"""JudgeAgent — scores every ping on a 5-dimension rubric and declares a
non-tie winner. No RAG, no web search (intentionally not a fact-checker).
See docs/PRD_judge.md."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from debate.services.agents._json_block import JSON_BLOCK_RE
from debate.services.agents._judge_helpers import (
    detect_collusion,
    extract_key_points,
    is_concession,
    tie_break,
)
from debate.services.agents.base_agent import BaseAgent
from debate.shared.schemas import Ping, Score, Side, Verdict
from debate.shared.skill_loader import load_skill

DEFAULT_SKILL_PATH = Path("skills/judge")


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
        """Score one ping on the 5-dimension rubric (0-3 each).

        Prompts the LLM side-blind (no side label) to reduce persona bias;
        zeroes ``clash`` on a detected concession (anti-collusion); stamps the
        side deterministically in code. Appends to ``self.scores`` and returns it.
        """
        prompt = (
            f"Score this ping (round {ping.round}):\n\n"
            f"{ping.text}\n\n"
            "Score the rubric dimensions on the merits of THIS ping alone. "
            "Do not anchor on which side authored it or on the side's "
            "expected rhetorical style — score what is actually on the page.\n"
            "Reply with ONE JSON object matching the per-ping rubric schema."
        )
        response = self.generate(prompt)
        payload = self._parse_or_repair(response.text, "per-ping rubric schema")
        if is_concession(ping.text):
            payload["clash"] = 0
        payload.update({"ping_round": ping.round, "side": ping.side})
        score = Score.model_validate(payload)
        self.scores.append(score)
        return score

    def decide_winner(self, pings: list[Ping]) -> Verdict:
        """Synthesize the final verdict from accumulated scores.

        Totals are summed in code (not trusted to the LLM); on an exact tie the
        deterministic ``tie_break`` cascade picks the winner and its rationale is
        prepended so the text can never contradict the recorded winner. Ties are
        therefore impossible. Returns the validated ``Verdict``.
        """
        dogs_total = sum(self._total(s) for s in self.scores if s.side == "dogs")
        cats_total = sum(self._total(s) for s in self.scores if s.side == "cats")
        prompt = (
            f"Final scores — dogs: {dogs_total}, cats: {cats_total}.\n"
            f"Score detail: {[s.model_dump() for s in self.scores]}\n"
            "Deliver the verdict as ONE JSON object."
        )
        response = self.generate(prompt)
        payload = self._parse_or_repair(response.text, "final verdict schema")
        payload["dogs_total"] = dogs_total
        payload["cats_total"] = cats_total
        payload["margin"] = abs(dogs_total - cats_total)
        if dogs_total == cats_total:
            winner, explanation = tie_break(self.scores)
            payload["winner"] = winner
            payload["margin"] = 0
            llm_rationale = (payload.get("written_rationale") or "").strip()
            payload["written_rationale"] = (
                f"{explanation} {llm_rationale}".strip() if llm_rationale else explanation
            )
        payload.setdefault("key_points_dogs", extract_key_points(pings, "dogs"))
        payload.setdefault("key_points_cats", extract_key_points(pings, "cats"))
        return Verdict.model_validate(payload)

    def receive(self, envelope: object) -> Score | Verdict | None:
        if isinstance(envelope, Ping):
            return self.score_ping(envelope)
        if isinstance(envelope, FinalizeRequest):
            return self.decide_winner(envelope.pings)
        return None

    def _tie_break(self) -> Side:
        """Back-compat shim — delegates to the helper module so existing
        tests that reach into `JudgeAgent._tie_break()` keep working."""
        return tie_break(self.scores)[0]

    @staticmethod
    def _is_concession(text: str) -> bool:
        return is_concession(text)

    @staticmethod
    def _detect_collusion(recent_pings: list[Ping], window: int = 3) -> bool:
        return detect_collusion(recent_pings, window)

    @staticmethod
    def _extract_key_points(pings: list[Ping], side: Side, k: int = 3) -> list[str]:
        return extract_key_points(pings, side, k)

    @staticmethod
    def _total(score: Score) -> int:
        return score.structure + score.logos + score.pathos + score.ethos + score.clash

    @staticmethod
    def _extract_json(text: str) -> dict:
        match = JSON_BLOCK_RE.search(text)
        if not match:
            raise ValueError("no JSON in judge reply")
        cleaned = re.sub(r",\s*([}\]])", r"\1", match.group(0))
        return json.loads(cleaned)

    def _parse_or_repair(self, text: str, schema_hint: str) -> dict:
        """Strict parse first; on failure, ask the LLM to re-emit valid JSON once.
        Trailing-comma tolerance is in `_extract_json`; this layer catches deeper
        malformations (missing braces, unquoted keys) that would otherwise abort
        a 20-ping debate over a single bad reply."""
        try:
            return self._extract_json(text)
        except (json.JSONDecodeError, ValueError):
            repair_prompt = (
                f"Your previous reply was not valid JSON. Re-emit ONE JSON object "
                f"matching the {schema_hint}. No prose outside JSON. "
                f"Previous reply:\n{text}"
            )
            retry = self.generate(repair_prompt)
            return self._extract_json(retry.text)
