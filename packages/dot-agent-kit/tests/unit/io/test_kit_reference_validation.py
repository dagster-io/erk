"""Tests for kit reference validation module."""

from pathlib import Path

import pytest

from dot_agent_kit.io.kit_reference_validation import (
    KitReferenceError,
    validate_kit_references,
)


class TestValidateKitReferences:
    """Tests for validate_kit_references function."""

    def test_valid_kit_all_references_declared(self, tmp_path: Path) -> None:
        """Test kit with all references declared passes validation."""
        # Create kit structure
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        # Create skill that references a doc
        skill_dir = kit_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "# My Skill\n\n@.claude/docs/my-kit/guide.md\n",
            encoding="utf-8",
        )

        # Create doc in kit source
        doc_dir = kit_dir / "docs" / "my-kit"
        doc_dir.mkdir(parents=True)
        doc_file = doc_dir / "guide.md"
        doc_file.write_text("# Guide", encoding="utf-8")

        # Create manifest with both skill and doc
        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/my-skill/SKILL.md
  doc:
    - docs/my-kit/guide.md
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 0

    def test_kit_with_missing_doc_reference(self, tmp_path: Path) -> None:
        """Test kit with undeclared doc reference fails validation."""
        # Create kit structure
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        # Create skill that references a doc NOT in manifest
        skill_dir = kit_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "# My Skill\n\n@.claude/docs/my-kit/undeclared.md\n",
            encoding="utf-8",
        )

        # Create manifest with skill but NOT the doc
        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/my-skill/SKILL.md
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 1
        assert errors[0].source_artifact == "skills/my-skill/SKILL.md"
        assert errors[0].reference == ".claude/docs/my-kit/undeclared.md"
        assert errors[0].error_type == "missing_in_manifest"
        assert errors[0].suggested_fix is not None
        assert "docs/my-kit/undeclared.md" in errors[0].suggested_fix

    def test_relative_references_skipped(self, tmp_path: Path) -> None:
        """Test that relative references (not .claude/) are skipped."""
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        # Create skill with relative reference
        skill_dir = kit_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "# My Skill\n\n@../shared/utils.md\n",
            encoding="utf-8",
        )

        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/my-skill/SKILL.md
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 0

    def test_kit_with_no_markdown_artifacts(self, tmp_path: Path) -> None:
        """Test kit with no markdown artifacts passes trivially."""
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts: {}
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 0

    def test_nonexistent_manifest_returns_empty(self, tmp_path: Path) -> None:
        """Test that nonexistent manifest returns empty list."""
        manifest_path = tmp_path / "nonexistent" / "kit.yaml"
        errors = validate_kit_references(manifest_path)
        assert len(errors) == 0

    def test_multiple_references_multiple_errors(self, tmp_path: Path) -> None:
        """Test that multiple missing references return multiple errors."""
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        # Create skill that references two undeclared docs
        skill_dir = kit_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """# My Skill

@.claude/docs/my-kit/first.md
@.claude/docs/my-kit/second.md
""",
            encoding="utf-8",
        )

        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/my-skill/SKILL.md
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 2
        refs = {e.reference for e in errors}
        assert ".claude/docs/my-kit/first.md" in refs
        assert ".claude/docs/my-kit/second.md" in refs

    def test_skill_reference_detection(self, tmp_path: Path) -> None:
        """Test that skill references are detected correctly."""
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        # Create doc that references a skill
        doc_dir = kit_dir / "docs" / "my-kit"
        doc_dir.mkdir(parents=True)
        doc_file = doc_dir / "guide.md"
        doc_file.write_text(
            "# Guide\n\n@.claude/skills/my-kit/SKILL.md\n",
            encoding="utf-8",
        )

        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts:
  doc:
    - docs/my-kit/guide.md
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 1
        assert errors[0].suggested_fix is not None
        assert "skill" in errors[0].suggested_fix

    def test_code_block_references_ignored(self, tmp_path: Path) -> None:
        """Test that @ references in code blocks are ignored."""
        kit_dir = tmp_path / "my-kit"
        kit_dir.mkdir()

        skill_dir = kit_dir / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """# My Skill

```python
@decorator
def foo():
    pass
```

Normal content.
""",
            encoding="utf-8",
        )

        manifest_path = kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: my-kit
version: 1.0.0
description: Test kit
artifacts:
  skill:
    - skills/my-skill/SKILL.md
""",
            encoding="utf-8",
        )

        errors = validate_kit_references(manifest_path)
        assert len(errors) == 0


class TestKitReferenceError:
    """Tests for KitReferenceError dataclass."""

    def test_error_fields(self) -> None:
        """Test KitReferenceError fields."""
        error = KitReferenceError(
            source_artifact="skills/my-skill/SKILL.md",
            reference=".claude/docs/missing.md",
            error_type="missing_in_manifest",
            suggested_fix="Add 'docs/missing.md' to kit.yaml",
        )

        assert error.source_artifact == "skills/my-skill/SKILL.md"
        assert error.reference == ".claude/docs/missing.md"
        assert error.error_type == "missing_in_manifest"
        assert error.suggested_fix == "Add 'docs/missing.md' to kit.yaml"

    def test_error_frozen(self) -> None:
        """Test that KitReferenceError is frozen."""
        error = KitReferenceError(
            source_artifact="skills/my-skill/SKILL.md",
            reference=".claude/docs/missing.md",
            error_type="missing_in_manifest",
            suggested_fix=None,
        )

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            error.source_artifact = "different"  # type: ignore[misc]
