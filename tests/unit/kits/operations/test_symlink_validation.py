"""Tests for symlink validation module."""

from pathlib import Path

from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.operations.symlink_validation import (
    SymlinkValidationResult,
    validate_skill_symlinks,
)


def test_validate_no_skills_returns_valid(tmp_path: Path) -> None:
    """Test that validation passes when there are no skills."""
    config = ProjectConfig(version="1", kits={})
    result = validate_skill_symlinks(tmp_path, config)

    assert result.is_valid
    assert len(result.issues) == 0


def test_validate_none_config_returns_valid(tmp_path: Path) -> None:
    """Test that validation passes when config is None."""
    result = validate_skill_symlinks(tmp_path, None)

    assert result.is_valid
    assert len(result.issues) == 0


def test_validate_valid_two_stage_installation(tmp_path: Path) -> None:
    """Test that a correctly installed skill passes validation."""
    # Set up valid two-stage installation
    erk_skill = tmp_path / ".erk" / "skills" / "my-skill"
    erk_skill.mkdir(parents=True)
    (erk_skill / "SKILL.md").write_text("# My Skill", encoding="utf-8")

    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "my-skill").symlink_to("../../.erk/skills/my-skill")

    # Create config with managed skill
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/my-skill"],
        managed_skills=[".erk/skills/my-skill"],
    )
    config = ProjectConfig(version="1", kits={"test-kit": kit})

    result = validate_skill_symlinks(tmp_path, config)

    assert result.is_valid
    assert len(result.issues) == 0


def test_validate_missing_symlink_error(tmp_path: Path) -> None:
    """Test that missing symlink in .claude/skills is detected as error."""
    # Set up .erk/skills but no .claude symlink
    erk_skill = tmp_path / ".erk" / "skills" / "my-skill"
    erk_skill.mkdir(parents=True)
    (erk_skill / "SKILL.md").write_text("# My Skill", encoding="utf-8")

    # No symlink in .claude/skills
    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)

    # Create config with managed skill
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/my-skill"],
        managed_skills=[".erk/skills/my-skill"],
    )
    config = ProjectConfig(version="1", kits={"test-kit": kit})

    result = validate_skill_symlinks(tmp_path, config)

    assert not result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].severity == "error"
    assert result.issues[0].issue_type == "missing"
    assert "no symlink" in result.issues[0].message


def test_validate_broken_symlink_error(tmp_path: Path) -> None:
    """Test that broken symlink is detected as error."""
    # Create symlink but NOT the .erk/skills target
    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "my-skill").symlink_to("../../.erk/skills/my-skill")

    # No .erk/skills/my-skill directory

    # Create config with managed skill
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/my-skill"],
        managed_skills=[".erk/skills/my-skill"],
    )
    config = ProjectConfig(version="1", kits={"test-kit": kit})

    result = validate_skill_symlinks(tmp_path, config)

    assert not result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].severity == "error"
    assert result.issues[0].issue_type == "broken"
    assert "broken" in result.issues[0].message


def test_validate_regular_file_instead_of_symlink(tmp_path: Path) -> None:
    """Test that regular file instead of symlink is detected as error."""
    # Set up .erk/skills
    erk_skill = tmp_path / ".erk" / "skills" / "my-skill"
    erk_skill.mkdir(parents=True)
    (erk_skill / "SKILL.md").write_text("# My Skill", encoding="utf-8")

    # Create regular directory instead of symlink in .claude/skills
    claude_skill = tmp_path / ".claude" / "skills" / "my-skill"
    claude_skill.mkdir(parents=True)
    (claude_skill / "SKILL.md").write_text("# Copied content", encoding="utf-8")

    # Create config with managed skill
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/my-skill"],
        managed_skills=[".erk/skills/my-skill"],
    )
    config = ProjectConfig(version="1", kits={"test-kit": kit})

    result = validate_skill_symlinks(tmp_path, config)

    assert not result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].severity == "error"
    assert result.issues[0].issue_type == "missing"
    assert "regular file/directory" in result.issues[0].message


def test_validate_orphaned_erk_skill_warning(tmp_path: Path) -> None:
    """Test that skill in .erk/skills not tracked in config is a warning."""
    # Set up .erk/skills but don't track it in config
    erk_skill = tmp_path / ".erk" / "skills" / "orphaned-skill"
    erk_skill.mkdir(parents=True)
    (erk_skill / "SKILL.md").write_text("# Orphaned", encoding="utf-8")

    # Empty config (no managed skills)
    config = ProjectConfig(version="1", kits={})

    result = validate_skill_symlinks(tmp_path, config)

    # Should be valid (warnings don't make it invalid)
    assert result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"
    assert result.issues[0].issue_type == "orphaned"
    assert "not tracked" in result.issues[0].message


def test_validate_user_created_skill_ignored(tmp_path: Path) -> None:
    """Test that user-created skills in .claude/skills are ignored."""
    # Create user skill directly in .claude/skills (no .erk involvement)
    claude_skill = tmp_path / ".claude" / "skills" / "user-skill"
    claude_skill.mkdir(parents=True)
    (claude_skill / "SKILL.md").write_text("# User created", encoding="utf-8")

    # Empty config
    config = ProjectConfig(version="1", kits={})

    result = validate_skill_symlinks(tmp_path, config)

    # User-created skills are ignored
    assert result.is_valid
    assert len(result.issues) == 0


def test_validate_multiple_skills(tmp_path: Path) -> None:
    """Test validation with multiple skills from different kits."""
    # Set up multiple skills
    for skill_name in ["skill-a", "skill-b"]:
        erk_skill = tmp_path / ".erk" / "skills" / skill_name
        erk_skill.mkdir(parents=True)
        (erk_skill / "SKILL.md").write_text(f"# {skill_name}", encoding="utf-8")

    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "skill-a").symlink_to("../../.erk/skills/skill-a")
    (claude_skills / "skill-b").symlink_to("../../.erk/skills/skill-b")

    # Create config with multiple kits
    kit_a = InstalledKit(
        kit_id="kit-a",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/skill-a"],
        managed_skills=[".erk/skills/skill-a"],
    )
    kit_b = InstalledKit(
        kit_id="kit-b",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/skill-b"],
        managed_skills=[".erk/skills/skill-b"],
    )
    config = ProjectConfig(version="1", kits={"kit-a": kit_a, "kit-b": kit_b})

    result = validate_skill_symlinks(tmp_path, config)

    assert result.is_valid
    assert len(result.issues) == 0


def test_validation_result_is_valid_property() -> None:
    """Test SymlinkValidationResult.is_valid property."""
    from erk.kits.operations.symlink_validation import SymlinkIssue

    # No issues -> valid
    result = SymlinkValidationResult(issues=[])
    assert result.is_valid

    # Warning only -> valid
    result = SymlinkValidationResult(
        issues=[
            SymlinkIssue(
                severity="warning",
                issue_type="orphaned",
                path=Path(".erk/skills/test"),
                message="test warning",
            )
        ]
    )
    assert result.is_valid

    # Error -> invalid
    result = SymlinkValidationResult(
        issues=[
            SymlinkIssue(
                severity="error",
                issue_type="broken",
                path=Path(".claude/skills/test"),
                message="test error",
            )
        ]
    )
    assert not result.is_valid
