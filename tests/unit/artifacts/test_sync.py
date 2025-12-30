"""Tests for artifacts sync functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from erk.artifacts.state import load_artifact_state
from erk.artifacts.sync import SyncResult, _get_target_path, sync_artifacts
from erk.kits.models.kit import KitManifest


def test_sync_result_dataclass() -> None:
    """Test SyncResult dataclass creation."""
    result = SyncResult(
        success=True,
        artifacts_installed=5,
        hooks_installed=2,
    )

    assert result.success is True
    assert result.artifacts_installed == 5
    assert result.hooks_installed == 2
    assert result.error is None


def test_sync_result_with_error() -> None:
    """Test SyncResult with error field."""
    result = SyncResult(
        success=False,
        artifacts_installed=0,
        hooks_installed=0,
        error="Something went wrong",
    )

    assert result.success is False
    assert result.error == "Something went wrong"


def test_get_target_path_command(tmp_project: Path) -> None:
    """Test target path calculation for command artifacts."""
    target = _get_target_path(tmp_project, "command", "commands/erk/test.md")
    expected = tmp_project / ".claude" / "commands" / "erk" / "test.md"
    assert target == expected


def test_get_target_path_skill(tmp_project: Path) -> None:
    """Test target path calculation for skill artifacts."""
    target = _get_target_path(tmp_project, "skill", "skills/my-skill/SKILL.md")
    expected = tmp_project / ".claude" / "skills" / "my-skill" / "SKILL.md"
    assert target == expected


def test_get_target_path_doc(tmp_project: Path) -> None:
    """Test target path calculation for doc artifacts (special case).

    Doc artifacts strip the 'docs/' prefix since the target dir is .erk/docs/kits/
    which already implies the doc type.
    """
    target = _get_target_path(tmp_project, "doc", "docs/erk/EXAMPLES.md")
    # docs/erk/EXAMPLES.md -> strips "docs/" prefix -> .erk/docs/kits/erk/EXAMPLES.md
    expected = tmp_project / ".erk" / "docs" / "kits" / "erk" / "EXAMPLES.md"
    assert target == expected


def test_sync_artifacts_installs_and_saves_state(tmp_project: Path) -> None:
    """Test that sync_artifacts installs artifacts and saves state."""
    # Create a minimal kit structure for testing
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    # Create a test artifact
    commands_dir = kit_dir / "commands" / "test"
    commands_dir.mkdir(parents=True)
    test_artifact = commands_dir / "hello.md"
    test_artifact.write_text("# Test Command", encoding="utf-8")

    # Create a mock manifest
    mock_manifest = MagicMock(spec=KitManifest)
    mock_manifest.name = "erk"
    mock_manifest.artifacts = {"command": ["commands/test/hello.md"]}
    mock_manifest.hooks = []

    with (
        patch("erk.artifacts.sync.get_current_version", return_value="1.2.3"),
        patch("erk_kits.get_kits_dir", return_value=tmp_project / "kits"),
        patch("erk.artifacts.sync.load_kit_manifest", return_value=mock_manifest),
    ):
        # Create the expected kit path
        erk_kit = tmp_project / "kits" / "erk"
        erk_kit.mkdir(parents=True)
        (erk_kit / "commands" / "test").mkdir(parents=True)
        (erk_kit / "commands" / "test" / "hello.md").write_text(
            "# Test Command", encoding="utf-8"
        )

        result = sync_artifacts(tmp_project)

    assert result.success is True
    assert result.artifacts_installed == 1
    assert result.hooks_installed == 0

    # Verify state was saved
    state = load_artifact_state(tmp_project)
    assert state is not None
    assert state.version == "1.2.3"


def test_sync_artifacts_creates_parent_dirs(tmp_project: Path) -> None:
    """Test that sync_artifacts creates parent directories for artifacts."""
    mock_manifest = MagicMock(spec=KitManifest)
    mock_manifest.name = "erk"
    mock_manifest.artifacts = {"command": ["commands/nested/deep/test.md"]}
    mock_manifest.hooks = []

    with (
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
        patch("erk_kits.get_kits_dir", return_value=tmp_project / "kits"),
        patch("erk.artifacts.sync.load_kit_manifest", return_value=mock_manifest),
    ):
        # Create the expected kit path with nested artifact
        erk_kit = tmp_project / "kits" / "erk"
        nested_dir = erk_kit / "commands" / "nested" / "deep"
        nested_dir.mkdir(parents=True)
        (nested_dir / "test.md").write_text("# Deep Test", encoding="utf-8")

        result = sync_artifacts(tmp_project)

    assert result.success is True

    # Verify the nested directory was created
    target_path = tmp_project / ".claude" / "commands" / "nested" / "deep" / "test.md"
    assert target_path.exists()


def test_sync_artifacts_skips_missing_source_files(tmp_project: Path) -> None:
    """Test that sync_artifacts skips artifacts that don't exist in source."""
    mock_manifest = MagicMock(spec=KitManifest)
    mock_manifest.name = "erk"
    mock_manifest.artifacts = {"command": ["commands/missing.md"]}
    mock_manifest.hooks = []

    with (
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
        patch("erk_kits.get_kits_dir", return_value=tmp_project / "kits"),
        patch("erk.artifacts.sync.load_kit_manifest", return_value=mock_manifest),
    ):
        # Create kit dir but NOT the artifact
        erk_kit = tmp_project / "kits" / "erk"
        erk_kit.mkdir(parents=True)

        result = sync_artifacts(tmp_project)

    # Should succeed but with 0 artifacts installed
    assert result.success is True
    assert result.artifacts_installed == 0
