"""Tests for publish_release command.

These tests verify:
- CLI command registration and basic invocation
- Validation logic for missing artifacts
- Error messages guide user correctly
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk_dev.cli import cli
from erk_dev.commands.publish_release.command import validate_artifacts_exist
from erk_dev.commands.publish_to_pypi.shared import PackageInfo


def test_publish_release_command_registered() -> None:
    """Verify publish-release command is registered in CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["publish-release", "--help"])

    assert result.exit_code == 0
    assert "Publish prepared artifacts to PyPI" in result.output
    assert "--dry-run" in result.output


def test_publish_release_fails_outside_repo_root(tmp_path: Path) -> None:
    """Test that publish-release fails when not in repo root."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["publish-release"])

    assert result.exit_code == 1
    assert "Not in repository root" in result.output


def test_validate_artifacts_exist_fails_when_dist_missing(tmp_path: Path) -> None:
    """Test that validation fails when dist directory doesn't exist."""
    packages = [
        PackageInfo(
            name="test-pkg",
            path=tmp_path,
            pyproject_path=tmp_path / "pyproject.toml",
        )
    ]
    staging_dir = tmp_path / "dist"

    with patch("erk_dev.commands.publish_release.command.user_output") as mock_output:
        try:
            validate_artifacts_exist(packages, staging_dir, "0.1.0", dry_run=False)
            raise AssertionError("Expected SystemExit")
        except SystemExit as e:
            assert e.code == 1

    # Verify helpful error message
    calls = [str(call) for call in mock_output.call_args_list]
    assert any("No artifacts found" in str(call) for call in calls)
    assert any("make prepare" in str(call) for call in calls)


def test_validate_artifacts_exist_fails_when_wheel_missing(tmp_path: Path) -> None:
    """Test that validation fails when wheel is missing."""
    packages = [
        PackageInfo(
            name="test-pkg",
            path=tmp_path,
            pyproject_path=tmp_path / "pyproject.toml",
        )
    ]
    staging_dir = tmp_path / "dist"
    staging_dir.mkdir()

    with patch("erk_dev.commands.publish_release.command.user_output") as mock_output:
        try:
            validate_artifacts_exist(packages, staging_dir, "0.1.0", dry_run=False)
            raise AssertionError("Expected SystemExit")
        except SystemExit as e:
            assert e.code == 1

    # Verify helpful error message
    calls = [str(call) for call in mock_output.call_args_list]
    assert any("Missing wheel" in str(call) for call in calls)
    assert any("make prepare" in str(call) for call in calls)


def test_validate_artifacts_exist_fails_when_sdist_missing(tmp_path: Path) -> None:
    """Test that validation fails when sdist is missing."""
    packages = [
        PackageInfo(
            name="test-pkg",
            path=tmp_path,
            pyproject_path=tmp_path / "pyproject.toml",
        )
    ]
    staging_dir = tmp_path / "dist"
    staging_dir.mkdir()

    # Create wheel but not sdist
    wheel = staging_dir / "test_pkg-0.1.0-py3-none-any.whl"
    wheel.write_text("", encoding="utf-8")

    with patch("erk_dev.commands.publish_release.command.user_output") as mock_output:
        try:
            validate_artifacts_exist(packages, staging_dir, "0.1.0", dry_run=False)
            raise AssertionError("Expected SystemExit")
        except SystemExit as e:
            assert e.code == 1

    # Verify helpful error message
    calls = [str(call) for call in mock_output.call_args_list]
    assert any("Missing sdist" in str(call) for call in calls)
    assert any("make prepare" in str(call) for call in calls)


def test_validate_artifacts_exist_succeeds_when_all_present(tmp_path: Path) -> None:
    """Test that validation succeeds when all artifacts are present."""
    packages = [
        PackageInfo(
            name="test-pkg",
            path=tmp_path,
            pyproject_path=tmp_path / "pyproject.toml",
        )
    ]
    staging_dir = tmp_path / "dist"
    staging_dir.mkdir()

    # Create both wheel and sdist
    wheel = staging_dir / "test_pkg-0.1.0-py3-none-any.whl"
    wheel.write_text("", encoding="utf-8")
    sdist = staging_dir / "test_pkg-0.1.0.tar.gz"
    sdist.write_text("", encoding="utf-8")

    with patch("erk_dev.commands.publish_release.command.user_output") as mock_output:
        # Should not raise
        validate_artifacts_exist(packages, staging_dir, "0.1.0", dry_run=False)

    # Verify success message
    calls = [str(call) for call in mock_output.call_args_list]
    assert any("All artifacts validated" in str(call) for call in calls)


def test_validate_artifacts_exist_dry_run_skips_validation(tmp_path: Path) -> None:
    """Test that dry-run mode skips actual validation."""
    packages = [
        PackageInfo(
            name="test-pkg",
            path=tmp_path,
            pyproject_path=tmp_path / "pyproject.toml",
        )
    ]
    staging_dir = tmp_path / "dist"
    # Note: dist directory doesn't exist

    with patch("erk_dev.commands.publish_release.command.user_output") as mock_output:
        # Should not raise in dry-run mode
        validate_artifacts_exist(packages, staging_dir, "0.1.0", dry_run=True)

    # Verify dry-run message
    calls = [str(call) for call in mock_output.call_args_list]
    assert any("DRY RUN" in str(call) for call in calls)


def test_publish_release_dry_run_shows_banner() -> None:
    """Test that dry-run mode shows appropriate banner."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create minimal pyproject.toml
        Path("pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")

        with patch(
            "erk_dev.commands.publish_release.command.get_workspace_packages"
        ) as mock_packages:
            mock_packages.side_effect = SystemExit(1)  # Stop early for this test

            result = runner.invoke(cli, ["publish-release", "--dry-run"])

    assert "[DRY RUN MODE" in result.output
