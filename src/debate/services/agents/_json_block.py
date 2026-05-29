"""Shared compiled regex for pulling the first JSON object out of an LLM reply.

Used by both the debate-agent ping parser (`_debate_agent_helpers`) and the
judge's score/verdict parser (`judge_agent`). Extracted here so the pattern
lives in exactly one place (CLAUDE.md §4 DRY). The surrounding parse logic
differs per caller and stays in each module.
"""

from __future__ import annotations

import re

# Greedy + DOTALL: span from the first "{" to the last "}", so a JSON object
# wrapped in prose / code fences is still captured whole.
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
