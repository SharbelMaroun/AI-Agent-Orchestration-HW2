"""Unit tests for debate.shared.skill_loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from debate.shared.skill_loader import load_skill


def _write_skill(tmp_path: Path, body: str, with_frontmatter: bool = True) -> Path:
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    if with_frontmatter:
        content = "---\nname: test\ndescription: a test skill\n---\n\n" + body
    else:
        content = body
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


def test_load_from_directory_strips_frontmatter(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "You are a test agent.\n")
    body = load_skill(skill_dir)
    assert body == "You are a test agent."
    assert "name: test" not in body


def test_load_from_explicit_skill_md_path(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "Direct file path.\n")
    body = load_skill(skill_dir / "SKILL.md")
    assert body == "Direct file path."


def test_load_no_frontmatter_returns_raw(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "Just body, no frontmatter.\n", with_frontmatter=False)
    body = load_skill(skill_dir)
    assert body == "Just body, no frontmatter."


def test_load_malformed_frontmatter_falls_back_to_raw(tmp_path: Path) -> None:
    """If the opening `---` has no closing `---`, fall back to returning
    the whole file rather than silent emptiness."""
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    raw = "---\nname: bad\nno closing delim, just body text\n"
    (skill_dir / "SKILL.md").write_text(raw, encoding="utf-8")
    body = load_skill(skill_dir)
    assert "no closing delim" in body


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_skill(tmp_path / "does_not_exist")


def test_load_real_dogs_skill_works() -> None:
    """Smoke: the actual shipped skill file loads and contains the
    Dogs Advocate marker."""
    body = load_skill("skills/dogs")
    assert "Dogs Advocate" in body


def test_load_real_cats_skill_works() -> None:
    body = load_skill("skills/cats")
    assert "Cats Advocate" in body


def test_load_real_judge_skill_works() -> None:
    body = load_skill("skills/judge")
    assert "Judge" in body
