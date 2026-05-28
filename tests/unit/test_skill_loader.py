"""Unit tests for debate.shared.skill_loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from debate.shared.skill_loader import load_agent_skills, load_skill


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


def test_load_agent_skills_composes_persona_and_auxiliary(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "I am the persona.\n")
    aux = skill_dir / "auxiliary"
    aux.mkdir()
    (aux / "alpha.md").write_text("---\nname: alpha\n---\n\nAlpha body.", encoding="utf-8")
    (aux / "beta.md").write_text("Beta body, no frontmatter.", encoding="utf-8")
    body = load_agent_skills(skill_dir)
    assert "I am the persona." in body
    assert "## Skill: alpha" in body
    assert "Alpha body." in body
    assert "## Skill: beta" in body
    assert "Beta body" in body
    assert body.index("alpha") < body.index("beta")  # sorted load order


def test_load_agent_skills_no_auxiliary_returns_persona_only(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "Just the persona.\n")
    body = load_agent_skills(skill_dir)
    assert body == "Just the persona."


def test_load_agent_skills_real_dogs_includes_all_four_auxiliary() -> None:
    body = load_agent_skills("skills/dogs")
    for name in ("evidence_health", "evidence_utility", "evidence_bonding", "rebuttal_aloofness"):
        assert f"## Skill: {name}" in body


def test_load_agent_skills_real_cats_includes_all_six_auxiliary() -> None:
    """Cats has 6 auxiliary skills vs Dogs' 4 — intentional asymmetry to
    counterbalance Dogs' multi-skill dimension-stacking advantage. 5th
    skill (`empirical_independence`) added 2026-05-28 for logos parity;
    6th (`expert_authority`) added same day after the pathos-quota revert
    pointed to ethos as the remaining Dogs advantage. See README
    "Updated result after 19 saved debates"."""
    body = load_agent_skills("skills/cats")
    for name in (
        "culture_literary",
        "empirical_independence",
        "expert_authority",
        "imagery_warmth",
        "rebuttal_utility",
        "socratic_moves",
    ):
        assert f"## Skill: {name}" in body
