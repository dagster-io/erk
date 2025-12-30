"""Tests for artifact sync."""

from pathlib import Path
from unittest.mock import patch

from erk.artifacts.sync import sync_artifacts


def test_sync_artifacts_skips_in_erk_repo(tmp_path: Path) -> None:
    """Skips sync when running in erk repo."""
    # Create pyproject.toml with erk name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    result = sync_artifacts(tmp_path, force=False)

    assert result.success is True
    assert result.artifacts_installed == 0
    assert "erk repo" in result.message


def test_sync_artifacts_fails_when_bundled_not_found(tmp_path: Path) -> None:
    """Fails when bundled .claude/ directory doesn't exist."""
    nonexistent = tmp_path / "nonexistent"
    with patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=nonexistent):
        result = sync_artifacts(tmp_path, force=False)

    assert result.success is False
    assert result.artifacts_installed == 0
    assert "not found" in result.message


def test_sync_artifacts_copies_files(tmp_path: Path) -> None:
    """Copies artifact files from bundled to target."""
    # Create bundled artifacts directory
    bundled_dir = tmp_path / "bundled"
    skill_dir = bundled_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Create target directory (different from bundled)
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir):
        with patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"):
            result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    assert result.artifacts_installed == 1

    # Verify file was copied
    copied_file = target_dir / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert copied_file.exists()
    assert copied_file.read_text(encoding="utf-8") == "# Test Skill"


def test_sync_artifacts_saves_state(tmp_path: Path) -> None:
    """Saves state with current version after sync."""
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir):
        with patch("erk.artifacts.sync.get_current_version", return_value="2.0.0"):
            sync_artifacts(target_dir, force=False)

    # Verify state was saved
    state_file = target_dir / ".erk" / "state.toml"
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")
    assert 'version = "2.0.0"' in content
