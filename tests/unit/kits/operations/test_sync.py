"""Tests for sync operations."""

from pathlib import Path

from erk.kits.operations.sync import _remove_managed_skills


def test_remove_managed_skills_removes_directory(tmp_path: Path) -> None:
    """Test that _remove_managed_skills removes skill directories."""
    # Create a managed skill in .erk/skills/
    erk_skills = tmp_path / ".erk" / "skills" / "my-skill"
    erk_skills.mkdir(parents=True)
    (erk_skills / "SKILL.md").write_text("# Test", encoding="utf-8")

    managed_skills = [".erk/skills/my-skill"]

    _remove_managed_skills(managed_skills, tmp_path)

    assert not erk_skills.exists()


def test_remove_managed_skills_removes_symlink(tmp_path: Path) -> None:
    """Test that _remove_managed_skills removes symlinks (dev mode)."""
    # Create a symlink in .erk/skills/ (dev mode scenario)
    erk_skills = tmp_path / ".erk" / "skills"
    erk_skills.mkdir(parents=True)

    source_skill = tmp_path / "kit-source" / "skills" / "my-skill"
    source_skill.mkdir(parents=True)
    (source_skill / "SKILL.md").write_text("# Source", encoding="utf-8")

    symlink_path = erk_skills / "my-skill"
    symlink_path.symlink_to(source_skill)

    managed_skills = [".erk/skills/my-skill"]

    _remove_managed_skills(managed_skills, tmp_path)

    assert not symlink_path.exists()
    # Source should still exist
    assert source_skill.exists()


def test_remove_managed_skills_skips_nonexistent(tmp_path: Path) -> None:
    """Test that _remove_managed_skills gracefully handles nonexistent paths."""
    managed_skills = [".erk/skills/nonexistent-skill"]

    # Should not raise any exception
    _remove_managed_skills(managed_skills, tmp_path)


def test_remove_managed_skills_handles_multiple_skills(tmp_path: Path) -> None:
    """Test that _remove_managed_skills handles multiple skills."""
    # Create multiple managed skills
    for skill_name in ["skill-a", "skill-b"]:
        skill_path = tmp_path / ".erk" / "skills" / skill_name
        skill_path.mkdir(parents=True)
        (skill_path / "SKILL.md").write_text(f"# {skill_name}", encoding="utf-8")

    managed_skills = [".erk/skills/skill-a", ".erk/skills/skill-b"]

    _remove_managed_skills(managed_skills, tmp_path)

    assert not (tmp_path / ".erk" / "skills" / "skill-a").exists()
    assert not (tmp_path / ".erk" / "skills" / "skill-b").exists()
