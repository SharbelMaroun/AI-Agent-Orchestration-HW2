"""Skill loader — reads `skills/<name>/SKILL.md` files per Lesson 05 §5.

A Skill is a directory containing a `SKILL.md` file with YAML frontmatter
(name, description, …) followed by the system prompt body. The frontmatter
is metadata for the human / future Router-Skill — we strip it before
handing the body to the LLM so the model sees only the prompt.
"""

from __future__ import annotations

from pathlib import Path

FRONTMATTER_DELIM = "---"


def load_skill(skill_path: str | Path) -> str:
    """Return the body of a SKILL.md file (frontmatter stripped).

    Accepts either a path directly to `SKILL.md` or to the skill directory.
    Raises `FileNotFoundError` if the file doesn't exist.
    """
    path = Path(skill_path)
    if path.is_dir():
        path = path / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    return _strip_frontmatter(text)


def _strip_frontmatter(text: str) -> str:
    stripped = text.lstrip()
    if not stripped.startswith(FRONTMATTER_DELIM):
        return text.strip()
    # Split on the second '---' marker.
    parts = stripped.split(FRONTMATTER_DELIM, 2)
    if len(parts) < 3:
        # Malformed frontmatter — fall back to returning the raw text so the
        # caller at least gets something usable instead of silent emptiness.
        return text.strip()
    return parts[2].strip()
