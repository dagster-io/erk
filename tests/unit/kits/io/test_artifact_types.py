"""Tests for artifact types and target directories."""

from erk.kits.models.artifact import (
    ARTIFACT_TARGET_DIRS,
    ARTIFACT_TYPE_PLURALS,
)


def test_artifact_target_dirs_mapping() -> None:
    """Test ARTIFACT_TARGET_DIRS maps all artifact types to correct directories."""
    # Verify all standard artifact types go to .claude
    assert ARTIFACT_TARGET_DIRS["skill"] == ".claude"
    assert ARTIFACT_TARGET_DIRS["command"] == ".claude"
    assert ARTIFACT_TARGET_DIRS["agent"] == ".claude"
    assert ARTIFACT_TARGET_DIRS["hook"] == ".claude"
    assert ARTIFACT_TARGET_DIRS["doc"] == ".claude"

    # Verify workflow goes to .github
    assert ARTIFACT_TARGET_DIRS["workflow"] == ".github"


def test_artifact_type_plurals_includes_workflow() -> None:
    """Test ARTIFACT_TYPE_PLURALS includes workflow type."""
    assert "workflow" in ARTIFACT_TYPE_PLURALS
    assert ARTIFACT_TYPE_PLURALS["workflow"] == "workflows"


def test_all_artifact_types_have_target_dirs() -> None:
    """Test all artifact types in ARTIFACT_TYPE_PLURALS have a target dir."""
    for artifact_type in ARTIFACT_TYPE_PLURALS:
        assert artifact_type in ARTIFACT_TARGET_DIRS, (
            f"Artifact type '{artifact_type}' missing from ARTIFACT_TARGET_DIRS"
        )


def test_all_target_dirs_are_valid() -> None:
    """Test all target directories are valid directory names."""
    for artifact_type, target_dir in ARTIFACT_TARGET_DIRS.items():
        # Target dir should start with a dot (hidden directory)
        assert target_dir.startswith("."), f"Target dir for '{artifact_type}' should start with '.'"
        # Target dir should not end with a slash
        assert not target_dir.endswith("/"), (
            f"Target dir for '{artifact_type}' should not end with '/'"
        )
