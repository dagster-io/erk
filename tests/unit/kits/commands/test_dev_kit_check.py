"""Tests for dev kit-check command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.dev.kit_check import (
    KitCheckResult,
    MissingReference,
    check_kit_references,
    get_kit_artifact_paths,
    kit_check,
)


def test_get_kit_artifact_paths_empty_manifest(tmp_path: Path) -> None:
    """Test get_kit_artifact_paths with empty artifacts."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts: {}
""",
        encoding="utf-8",
    )

    paths = get_kit_artifact_paths(manifest_path)

    assert len(paths) == 0


def test_get_kit_artifact_paths_with_artifacts(tmp_path: Path) -> None:
    """Test get_kit_artifact_paths extracts all artifact paths."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/test/SKILL.md
  command:
    - commands/test/cmd.md
  doc:
    - docs/test/doc.md
""",
        encoding="utf-8",
    )

    paths = get_kit_artifact_paths(manifest_path)

    assert ".claude/skills/test/SKILL.md" in paths
    assert ".claude/commands/test/cmd.md" in paths
    assert ".claude/docs/test/doc.md" in paths
    assert len(paths) == 3


def test_check_kit_references_no_references(tmp_path: Path) -> None:
    """Test check_kit_references with artifact containing no @ references."""
    kit_path = tmp_path / "test-kit"
    kit_path.mkdir()

    # Create manifest
    manifest_path = kit_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/test/SKILL.md
""",
        encoding="utf-8",
    )

    # Create artifact without @ references
    skill_path = kit_path / "skills" / "test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """# Test Skill

This is a test skill with no @ references.
""",
        encoding="utf-8",
    )

    result = check_kit_references("test-kit", kit_path)

    assert result.is_valid
    assert len(result.missing_references) == 0


def test_check_kit_references_valid_reference(tmp_path: Path) -> None:
    """Test check_kit_references with valid @ reference to included artifact."""
    kit_path = tmp_path / "test-kit"
    kit_path.mkdir()

    # Create manifest with both skill and doc
    manifest_path = kit_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/test/SKILL.md
  doc:
    - docs/test/reference.md
""",
        encoding="utf-8",
    )

    # Create skill that references doc
    skill_path = kit_path / "skills" / "test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """# Test Skill

@.claude/docs/test/reference.md
""",
        encoding="utf-8",
    )

    # Create referenced doc
    doc_path = kit_path / "docs" / "test" / "reference.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("# Reference Doc\n", encoding="utf-8")

    result = check_kit_references("test-kit", kit_path)

    assert result.is_valid
    assert len(result.missing_references) == 0


def test_check_kit_references_missing_reference(tmp_path: Path) -> None:
    """Test check_kit_references detects missing @ reference."""
    kit_path = tmp_path / "test-kit"
    kit_path.mkdir()

    # Create manifest with only skill (no doc)
    manifest_path = kit_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/test/SKILL.md
""",
        encoding="utf-8",
    )

    # Create skill that references non-existent doc
    skill_path = kit_path / "skills" / "test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """# Test Skill

@.claude/docs/test/missing.md
""",
        encoding="utf-8",
    )

    result = check_kit_references("test-kit", kit_path)

    assert not result.is_valid
    assert len(result.missing_references) == 1
    assert result.missing_references[0].reference_path == ".claude/docs/test/missing.md"
    assert result.missing_references[0].line_number == 3


def test_check_kit_references_multiple_missing(tmp_path: Path) -> None:
    """Test check_kit_references detects multiple missing references."""
    kit_path = tmp_path / "test-kit"
    kit_path.mkdir()

    # Create manifest
    manifest_path = kit_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/test/SKILL.md
""",
        encoding="utf-8",
    )

    # Create skill with multiple missing references
    skill_path = kit_path / "skills" / "test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """# Test Skill

@.claude/docs/test/missing1.md

@.claude/docs/test/missing2.md
""",
        encoding="utf-8",
    )

    result = check_kit_references("test-kit", kit_path)

    assert not result.is_valid
    assert len(result.missing_references) == 2


def test_check_kit_references_reference_without_prefix(tmp_path: Path) -> None:
    """Test check_kit_references handles references without .claude/ prefix."""
    kit_path = tmp_path / "test-kit"
    kit_path.mkdir()

    # Create manifest with doc
    manifest_path = kit_path / "kit.yaml"
    manifest_path.write_text(
        """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/test/SKILL.md
  doc:
    - docs/test/reference.md
""",
        encoding="utf-8",
    )

    # Create skill that references doc without .claude/ prefix
    skill_path = kit_path / "skills" / "test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        """# Test Skill

@docs/test/reference.md
""",
        encoding="utf-8",
    )

    # Create referenced doc
    doc_path = kit_path / "docs" / "test" / "reference.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("# Reference Doc\n", encoding="utf-8")

    result = check_kit_references("test-kit", kit_path)

    # Should be valid because the physical file exists
    assert result.is_valid


def test_check_kit_references_no_manifest(tmp_path: Path) -> None:
    """Test check_kit_references with non-existent manifest."""
    kit_path = tmp_path / "test-kit"
    kit_path.mkdir()

    result = check_kit_references("test-kit", kit_path)

    # Should return valid with no missing references (nothing to check)
    assert result.is_valid
    assert len(result.missing_references) == 0


def test_kit_check_result_is_valid() -> None:
    """Test KitCheckResult.is_valid property."""
    valid_result = KitCheckResult(kit_name="test", missing_references=[])
    assert valid_result.is_valid

    invalid_result = KitCheckResult(
        kit_name="test",
        missing_references=[
            MissingReference(
                artifact_path=".claude/skills/test/SKILL.md",
                reference_path=".claude/docs/missing.md",
                line_number=5,
            )
        ],
    )
    assert not invalid_result.is_valid


def test_kit_check_command_help() -> None:
    """Test kit-check command shows help."""
    runner = CliRunner()
    result = runner.invoke(kit_check, ["--help"])

    assert result.exit_code == 0
    assert "Check kit integrity" in result.output
    assert "--kit" in result.output


def test_kit_check_command_invalid_kit_name() -> None:
    """Test kit-check command with non-existent kit name."""
    runner = CliRunner()
    result = runner.invoke(kit_check, ["--kit", "nonexistent-kit-xyz"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_kit_check_command_all_kits() -> None:
    """Test kit-check command runs on all bundled kits."""
    runner = CliRunner()
    result = runner.invoke(kit_check)

    # Should complete (either pass or fail, but not error)
    # The actual result depends on the state of bundled kits
    assert result.exit_code in (0, 1)


def test_missing_reference_dataclass() -> None:
    """Test MissingReference dataclass fields."""
    ref = MissingReference(
        artifact_path=".claude/skills/test/SKILL.md",
        reference_path=".claude/docs/test/doc.md",
        line_number=10,
    )

    assert ref.artifact_path == ".claude/skills/test/SKILL.md"
    assert ref.reference_path == ".claude/docs/test/doc.md"
    assert ref.line_number == 10
