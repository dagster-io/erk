"""Unit tests for upgrade command."""

import subprocess
from unittest.mock import MagicMock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands import upgrade as upgrade_module
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_upgrade_when_installed_less_than_required(monkeypatch) -> None:
    """Test that upgrade runs uv tool upgrade when installed < required."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory with required version file
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.5.0", encoding="utf-8")

        # Mock get_current_version to return older version
        monkeypatch.setattr(upgrade_module, "get_current_version", lambda: "0.4.0")

        # Mock subprocess.run to avoid actual upgrade
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stderr=""))
        monkeypatch.setattr(subprocess, "run", mock_run)

        ctx = env.build_context()
        result = runner.invoke(cli, ["upgrade"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Upgrading erk from 0.4.0 to 0.5.0" in result.output
        assert "Successfully upgraded" in result.output

        # Verify subprocess was called correctly
        mock_run.assert_called_once_with(
            ["uv", "tool", "upgrade", "erk"],
            capture_output=True,
            text=True,
        )


def test_upgrade_when_installed_equals_required(monkeypatch) -> None:
    """Test that upgrade shows 'already up to date' when installed = required."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory with required version file
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.4.2", encoding="utf-8")

        # Mock get_current_version to return same version
        monkeypatch.setattr(upgrade_module, "get_current_version", lambda: "0.4.2")

        ctx = env.build_context()
        result = runner.invoke(cli, ["upgrade"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Already up to date (0.4.2)" in result.output


def test_upgrade_when_installed_greater_than_required(monkeypatch) -> None:
    """Test that upgrade shows message when installed > required (no downgrade)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory with required version file
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.4.0", encoding="utf-8")

        # Mock get_current_version to return newer version
        monkeypatch.setattr(upgrade_module, "get_current_version", lambda: "0.4.3")

        ctx = env.build_context()
        result = runner.invoke(cli, ["upgrade"], obj=ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Already at 0.4.3" in result.output
        assert "repo requires 0.4.0" in result.output


def test_upgrade_when_no_version_file() -> None:
    """Test that upgrade errors when no version requirement file exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory but NO version file
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)

        ctx = env.build_context()
        result = runner.invoke(cli, ["upgrade"], obj=ctx)

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
        assert "No version requirement found" in result.output


def test_upgrade_handles_subprocess_failure(monkeypatch) -> None:
    """Test that upgrade handles uv tool upgrade failure."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory with required version file
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.5.0", encoding="utf-8")

        # Mock get_current_version to return older version
        monkeypatch.setattr(upgrade_module, "get_current_version", lambda: "0.4.0")

        # Mock subprocess.run to simulate failure
        mock_run = MagicMock(return_value=MagicMock(returncode=1, stderr="Package not found"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        ctx = env.build_context()
        result = runner.invoke(cli, ["upgrade"], obj=ctx)

        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
        assert "Upgrade failed" in result.output
        assert "Package not found" in result.output
