"""Tests for publish-release command.

These tests verify the publish-release workflow:
- Validates build artifacts exist in dist/
- Publishes packages to PyPI
- Pushes changes to remote
- Does NOT commit (assumes user already committed after prepare)
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
    from erk_dev.commands.publish_release.command import publish_release_workflow

    return publish_release_workflow


def get_validate_artifacts():
    """Lazy import to avoid circular dependency during test collection."""
    from erk_dev.commands.publish_release.command import validate_artifacts_exist

    return validate_artifacts_exist


@pytest.fixture
def mock_repo_root(tmp_path: Path) -> Path:
    """Create a mock repository root with pyproject.toml."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('version = "1.0.0"', encoding="utf-8")
    return repo


@pytest.fixture
def mock_dist_dir(tmp_path: Path) -> Path:
    """Create a mock dist/ directory with artifacts."""
    dist = tmp_path / "dist"
    dist.mkdir()
    # Create mock artifacts
    (dist / "test_pkg-1.0.0-py3-none-any.whl").write_text("", encoding="utf-8")
    (dist / "test_pkg-1.0.0.tar.gz").write_text("", encoding="utf-8")
    return dist


def test_publish_release_validates_repo_root(tmp_path: Path) -> None:
    """Test that publish-release exits if not in repository root."""
    no_repo = tmp_path / "not-a-repo"
    no_repo.mkdir()

    with patch("pathlib.Path.cwd", return_value=no_repo):
        with pytest.raises(SystemExit) as exc_info:
            get_workflow()(dry_run=False)
        assert exc_info.value.code == 1


def test_validate_artifacts_exist_missing_dist_dir(tmp_path: Path) -> None:
    """Test that validation fails when dist/ directory doesn't exist."""
    mock_package = MagicMock()
    mock_package.name = "test-pkg"
    packages = [mock_package]

    non_existent_dist = tmp_path / "dist"

    with pytest.raises(SystemExit) as exc_info:
        get_validate_artifacts()(packages, non_existent_dist, "1.0.0")
    assert exc_info.value.code == 1


def test_validate_artifacts_exist_missing_wheel(tmp_path: Path) -> None:
    """Test that validation fails when wheel artifact is missing."""
    mock_package = MagicMock()
    mock_package.name = "test-pkg"
    packages = [mock_package]

    dist = tmp_path / "dist"
    dist.mkdir()
    # Create only sdist, not wheel
    (dist / "test_pkg-1.0.0.tar.gz").write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        get_validate_artifacts()(packages, dist, "1.0.0")
    assert exc_info.value.code == 1


def test_validate_artifacts_exist_missing_sdist(tmp_path: Path) -> None:
    """Test that validation fails when sdist artifact is missing."""
    mock_package = MagicMock()
    mock_package.name = "test-pkg"
    packages = [mock_package]

    dist = tmp_path / "dist"
    dist.mkdir()
    # Create only wheel, not sdist
    (dist / "test_pkg-1.0.0-py3-none-any.whl").write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        get_validate_artifacts()(packages, dist, "1.0.0")
    assert exc_info.value.code == 1


def test_validate_artifacts_exist_success(tmp_path: Path) -> None:
    """Test that validation succeeds when all artifacts exist."""
    mock_package = MagicMock()
    mock_package.name = "test-pkg"
    packages = [mock_package]

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "test_pkg-1.0.0-py3-none-any.whl").write_text("", encoding="utf-8")
    (dist / "test_pkg-1.0.0.tar.gz").write_text("", encoding="utf-8")

    # Should not raise
    get_validate_artifacts()(packages, dist, "1.0.0")


def test_validate_artifacts_exist_handles_hyphen_normalization(tmp_path: Path) -> None:
    """Test that package names with hyphens are normalized correctly.

    Package name 'my-package' should look for 'my_package-1.0.0.whl'
    """
    mock_package = MagicMock()
    mock_package.name = "my-package"
    packages = [mock_package]

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "my_package-1.0.0-py3-none-any.whl").write_text("", encoding="utf-8")
    (dist / "my_package-1.0.0.tar.gz").write_text("", encoding="utf-8")

    # Should not raise - normalization should work
    get_validate_artifacts()(packages, dist, "1.0.0")


def test_publish_release_dry_run(mock_repo_root: Path, mock_dist_dir: Path) -> None:
    """Test that dry-run mode shows what would be done without making changes."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.publish_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.publish_release.command.get_current_version") as mock_version,
        patch("erk_dev.commands.publish_release.command.validate_artifacts_exist") as mock_validate,
        patch("erk_dev.commands.publish_release.command.publish_all_packages") as mock_publish,
        patch("erk_dev.commands.publish_release.command.push_to_remote") as mock_push,
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_version.return_value = "1.0.0"

        get_workflow()(dry_run=True)

        # Verify all steps were called with dry_run=True
        mock_validate.assert_called_once()
        mock_publish.assert_called_once_with([mock_package], mock_repo_root / "dist", "1.0.0", True)
        mock_push.assert_called_once_with(mock_repo_root, True)


def test_publish_release_success_workflow(mock_repo_root: Path) -> None:
    """Test successful publish-release workflow."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.publish_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.publish_release.command.get_current_version") as mock_version,
        patch("erk_dev.commands.publish_release.command.validate_artifacts_exist") as mock_validate,
        patch("erk_dev.commands.publish_release.command.publish_all_packages") as mock_publish,
        patch("erk_dev.commands.publish_release.command.push_to_remote") as mock_push,
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_version.return_value = "2.1.5"

        get_workflow()(dry_run=False)

        # Verify workflow steps in order
        mock_validate.assert_called_once()
        mock_publish.assert_called_once_with(
            [mock_package], mock_repo_root / "dist", "2.1.5", False
        )
        mock_push.assert_called_once_with(mock_repo_root, False)


def test_publish_release_fails_on_missing_artifacts(mock_repo_root: Path) -> None:
    """Test that publish-release exits if artifacts are missing."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.publish_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.publish_release.command.get_current_version") as mock_version,
    ):
        mock_package = MagicMock()
        mock_package.name = "test-pkg"
        mock_get_packages.return_value = [mock_package]
        mock_version.return_value = "1.0.0"

        # dist/ doesn't exist
        with pytest.raises(SystemExit) as exc_info:
            get_workflow()(dry_run=False)
        assert exc_info.value.code == 1


def test_publish_release_multiple_packages(mock_repo_root: Path) -> None:
    """Test publish-release with multiple packages."""
    with (
        patch("pathlib.Path.cwd", return_value=mock_repo_root),
        patch(
            "erk_dev.commands.publish_release.command.get_workspace_packages"
        ) as mock_get_packages,
        patch("erk_dev.commands.publish_release.command.get_current_version") as mock_version,
        patch("erk_dev.commands.publish_release.command.validate_artifacts_exist"),
        patch("erk_dev.commands.publish_release.command.publish_all_packages") as mock_publish,
        patch("erk_dev.commands.publish_release.command.push_to_remote"),
    ):
        pkg1 = MagicMock()
        pkg1.name = "package-one"
        pkg2 = MagicMock()
        pkg2.name = "package-two"
        mock_get_packages.return_value = [pkg1, pkg2]
        mock_version.return_value = "3.0.0"

        get_workflow()(dry_run=False)

        # Verify both packages are published
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert len(call_args[0][0]) == 2
        assert call_args[0][0][0].name == "package-one"
        assert call_args[0][0][1].name == "package-two"
        assert call_args[0][2] == "3.0.0"
