"""Shared helpers for the DebateSDK test files. Underscore prefix so pytest
does not collect this as a test module."""

from __future__ import annotations

import re as _re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from debate.sdk.sdk import DebateSDK
from debate.shared.config import load_setup
from debate.shared.schemas import CompletionResponse

NOW = datetime(2026, 5, 22, tzinfo=timezone.utc)
REPO_ROOT = Path(__file__).resolve().parents[2]

_OPP_ROUND_RE = _re.compile(r"Opponent's previous ping \(round (\d+)")


def fake_provider_factory(side_to_reply: dict[str, str] | None = None):
    """Factory that yields a MagicMock provider with canned debater / judge
    replies — used by every SDK test."""
    default_score = '{"structure":2,"logos":2,"pathos":2,"ethos":2,"clash":2,"rationale":"ok"}'
    default_verdict = '{"winner":"dogs","written_rationale":"clear"}'

    def factory(provider_name: str):
        provider = MagicMock()

        def complete(*, system, messages, model, max_tokens, timeout=None):
            del max_tokens, timeout
            last_user = messages[-1].content if messages else ""
            low = last_user.lower()
            if "final scores" in low or "deliver the verdict" in low:
                text = default_verdict
            elif "score this ping" in low:
                text = default_score
            else:
                m = _OPP_ROUND_RE.search(last_user)
                refers = m.group(1) if m else "null"
                text = f'{{"text":"argued","citations":[],"refers_to_ping":{refers}}}'
            return CompletionResponse(
                text=text,
                input_tokens=5,
                output_tokens=5,
                model=model,
                provider=provider_name,
            )

        provider.complete.side_effect = complete
        return provider

    return factory


def build_sdk(tmp_path: Path, num_rounds: int = 2) -> DebateSDK:
    setup = load_setup(REPO_ROOT / "config" / "setup.json")
    data = setup.model_dump()
    data["num_rounds"] = num_rounds
    setup = type(setup).model_validate(data)
    return DebateSDK(
        setup=setup,
        results_dir=tmp_path,
        provider_factory=fake_provider_factory(),
        wire_tools=False,
        use_processes=False,
    )
