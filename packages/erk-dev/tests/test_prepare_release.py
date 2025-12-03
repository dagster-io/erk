"""Tests for prepare-release command.

These tests verify the prepare-release workflow:
- Validates git status and branch sync
- Bumps patch version
- Synchronizes versions across packages
- Builds artifacts to dist/
- Does NOT commit or publish
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_user_output():
    """Mock user_output globally to avoid circular import issues."""
    with patch("erk_dev.cli.output.user_output"):
        yield


def get_workflow():
    """Lazy import to avoid circular dependency during test collection."""
    from erk_dev.commands.prepare_release.command import prepare_release_workflow

    return prepare_release_workflow


@pytest.fixture
def mock_repo_root(tmp_path: Path) -> Path:
    """Create a mock repository root with pyproject.toml."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('version = "1.0.0"', encoding="utf-8")
    return repo


def test_prepare_release_validates_repo_root(tmp_path: Path) -> None:
    """Test that prepare-release exits if not in repository root."""
    # Create a directory without pyproject.toml
    no_repo = tmp_path / "not-a-repo"
    no_repo.mkdir()

    with patch("pathlib.Path.cwd", return_value=no_repo):
        with pytest.raises(SystemExit) as exc_info:
            get_workflow()(dry_run=False)
        assert exc_info.value.code == 1


def test_prepare_release_dry_run(mock_repo_root: Path) -> None:
    """Test that dry-run mode shows what would be done without making changes."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.prepare_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.prepare_release.command.get_git_status") as mock_git_status,
        patch("erk_dev.commands.prepare_release.command.ensure_branch_is_in_sync") as mock_sync,
        patch("erk_dev.commands.prepare_release.command.run_git_pull") as mock_pull,
        patch(
            "erk_dev.commands.prepare_release.command.validate_version_consistency"
        ) as mock_validate,
        patch(
            "erk_dev.commands.prepare_release.command.synchronize_versions"
        ) as mock_sync_versions,
        patch("erk_dev.commands.prepare_release.command.run_uv_sync") as mock_uv,
        patch("erk_dev.commands.prepare_release.command.build_all_packages") as mock_build,
        patch("erk_dev.commands.prepare_release.command.validate_build_artifacts"),
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_git_status.return_value = ""
        mock_validate.return_value = "1.0.0"
        mock_build.return_value = mock_repo_root / "dist"

        get_workflow()(dry_run=True)

        # Verify all steps were called with dry_run=True
        mock_sync.assert_called_once_with(mock_repo_root, True)
        mock_pull.assert_called_once_with(mock_repo_root, True)
        mock_sync_versions.assert_called_once_with([mock_package], "1.0.0", "1.0.1", True)
        mock_uv.assert_called_once_with(mock_repo_root, True)
        mock_build.assert_called_once_with([mock_package], mock_repo_root, True)


def test_prepare_release_fails_on_uncommitted_changes(mock_repo_root: Path) -> None:
    """Test that prepare-release exits if there are uncommitted changes."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.prepare_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.prepare_release.command.get_git_status") as mock_git_status,
        patch("erk_dev.commands.prepare_release.command.filter_git_status") as mock_filter,
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_git_status.return_value = " M src/file.py"
        mock_filter.return_value = [" M src/file.py"]

        with pytest.raises(SystemExit) as exc_info:
            get_workflow()(dry_run=False)
        assert exc_info.value.code == 1


def test_prepare_release_success_workflow(mock_repo_root: Path) -> None:
    """Test successful prepare-release workflow."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.prepare_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.prepare_release.command.get_git_status") as mock_git_status,
        patch("erk_dev.commands.prepare_release.command.ensure_branch_is_in_sync") as mock_sync,
        patch("erk_dev.commands.prepare_release.command.run_git_pull") as mock_pull,
        patch(
            "erk_dev.commands.prepare_release.command.validate_version_consistency"
        ) as mock_validate,
        patch(
            "erk_dev.commands.prepare_release.command.synchronize_versions"
        ) as mock_sync_versions,
        patch("erk_dev.commands.prepare_release.command.run_uv_sync") as mock_uv,
        patch("erk_dev.commands.prepare_release.command.build_all_packages") as mock_build,
        patch(
            "erk_dev.commands.prepare_release.command.validate_build_artifacts"
        ) as mock_validate_artifacts,
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_git_status.return_value = ""
        mock_validate.return_value = "1.2.3"
        mock_build.return_value = mock_repo_root / "dist"

        get_workflow()(dry_run=False)

        # Verify workflow steps in order
        mock_sync.assert_called_once_with(mock_repo_root, False)
        mock_pull.assert_called_once_with(mock_repo_root, False)
        mock_validate.assert_called_once()
        mock_sync_versions.assert_called_once_with([mock_package], "1.2.3", "1.2.4", False)
        mock_uv.assert_called_once_with(mock_repo_root, False)
        mock_build.assert_called_once_with([mock_package], mock_repo_root, False)
        mock_validate_artifacts.assert_called_once()


def test_prepare_release_version_bump_logic(mock_repo_root: Path) -> None:
    """Test that version is correctly bumped from old to new."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.prepare_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.prepare_release.command.get_git_status") as mock_git_status,
        patch("erk_dev.commands.prepare_release.command.ensure_branch_is_in_sync"),
        patch("erk_dev.commands.prepare_release.command.run_git_pull"),
        patch(
            "erk_dev.commands.prepare_release.command.validate_version_consistency"
        ) as mock_validate,
        patch(
            "erk_dev.commands.prepare_release.command.synchronize_versions"
        ) as mock_sync_versions,
        patch("erk_dev.commands.prepare_release.command.run_uv_sync"),
        patch("erk_dev.commands.prepare_release.command.build_all_packages"),
        patch("erk_dev.commands.prepare_release.command.validate_build_artifacts"),
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_git_status.return_value = ""
        mock_validate.return_value = "2.5.9"

        get_workflow()(dry_run=False)

        # Verify version bump: 2.5.9 → 2.5.10
        mock_sync_versions.assert_called_once()
        call_args = mock_sync_versions.call_args
        assert call_args[0][1] == "2.5.9"  # old version
        assert call_args[0][2] == "2.5.10"  # new version
