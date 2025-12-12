"""Tests for outdated erk skill health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder import check_outdated_erk_skill


def test_check_outdated_erk_skill_passes_when_no_skill_dir(
    tmp_path: Path,
) -> None:
    """Test check passes when .claude/skills/erk/ doesn't exist."""
    result = check_outdated_erk_skill(tmp_path)
    assert result.passed is True
    assert "No outdated" in result.message


def test_check_outdated_erk_skill_passes_when_claude_dir_but_no_skill(
    tmp_path: Path,
) -> None:
    """Test check passes when .claude/ exists but not skills/erk/."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    result = check_outdated_erk_skill(tmp_path)
    assert result.passed is True
    assert "No outdated" in result.message


def test_check_outdated_erk_skill_passes_when_other_skills_exist(
    tmp_path: Path,
) -> None:
    """Test check passes when other skills exist but not erk."""
    skills_dir = tmp_path / ".claude" / "skills" / "other-skill"
    skills_dir.mkdir(parents=True)

    result = check_outdated_erk_skill(tmp_path)
    assert result.passed is True
    assert "No outdated" in result.message


def test_check_outdated_erk_skill_fails_when_erk_skill_exists(
    tmp_path: Path,
) -> None:
    """Test check fails when outdated erk skill directory exists."""
    skill_dir = tmp_path / ".claude" / "skills" / "erk"
    skill_dir.mkdir(parents=True)

    result = check_outdated_erk_skill(tmp_path)

    assert result.passed is False
    assert result.name == "outdated erk skill"
    assert ".claude/skills/erk/" in result.message
    assert result.details is not None
    assert "rm -rf" in result.details
    assert "Remediation" in result.details
