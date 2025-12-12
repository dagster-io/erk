"""Tests for artifact validation."""

from pathlib import Path

from erk.kits.io.state import create_default_config, save_project_config
from erk.kits.models.config import InstalledKit
from erk.kits.operations.validation import validate_artifact, validate_project


def test_validate_artifact_valid(tmp_path: Path) -> None:
    """Test validating a valid artifact."""
    artifact = tmp_path / "test.md"
    artifact.write_text(
        "---\nname: test-agent\ndescription: A test agent\n---\n\n# Test Agent",
        encoding="utf-8",
    )

    result = validate_artifact(artifact)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_artifact_nonexistent(tmp_path: Path) -> None:
    """Test validating non-existent artifact."""
    artifact = tmp_path / "nonexistent.md"

    result = validate_artifact(artifact)
    assert result.is_valid is False
    assert any("does not exist" in e for e in result.errors)


def test_validate_project(tmp_path: Path) -> None:
    """Test validating project with managed artifacts."""
    # Create .claude directory structure
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    # Create a skill
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill",
        encoding="utf-8",
    )

    # Create config with managed artifact
    config = create_default_config()
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=["skills/test-skill/SKILL.md"],
    )
    config = config.update_kit(kit)
    save_project_config(tmp_path, config)

    # Validate
    results = validate_project(tmp_path)

    assert len(results) == 1
    result = results[0]
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_project_missing_artifact(tmp_path: Path) -> None:
    """Test validating project with missing managed artifact."""
    # Create .claude directory but no artifacts
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create config with managed artifact that doesn't exist
    config = create_default_config()
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="package",
        version="1.0.0",
        artifacts=["skills/missing-skill/SKILL.md"],
    )
    config = config.update_kit(kit)
    save_project_config(tmp_path, config)

    # Validate
    results = validate_project(tmp_path)

    assert len(results) == 1
    result = results[0]
    assert result.is_valid is False
    assert any("does not exist" in e for e in result.errors)


def test_validate_project_no_claude_dir(tmp_path: Path) -> None:
    """Test validating project with no .claude directory."""
    # Create config but no .claude directory
    config = create_default_config()
    save_project_config(tmp_path, config)

    # Validate
    results = validate_project(tmp_path)

    assert len(results) == 0  # No validation results if no .claude dir
