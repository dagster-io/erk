"""Tests for artifacts CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk.artifacts.models import ArtifactState
from erk.artifacts.state import save_artifact_state
from erk.cli.commands.artifacts.check import check
from erk.cli.commands.artifacts.sync import sync


def test_check_command_not_initialized(tmp_path: Path) -> None:
    """Test check command when project is not initialized."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        with patch(
            "erk.cli.commands.artifacts.check.get_current_version", return_value="1.0.0"
        ):
            result = runner.invoke(check)

    assert result.exit_code == 0
    assert "erk version: 1.0.0" in result.output
    assert "not initialized" in result.output


def test_check_command_up_to_date(tmp_path: Path) -> None:
    """Test check command when artifacts are up to date."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        save_artifact_state(project_dir, ArtifactState(version="1.0.0"))

        # Need to patch both the version getter AND check_staleness at their usage sites
        with (
            patch(
                "erk.cli.commands.artifacts.check.get_current_version",
                return_value="1.0.0",
            ),
            patch("erk.cli.commands.artifacts.check.check_staleness") as mock_check,
        ):
            mock_check.return_value = MagicMock(
                is_stale=False, reason="up to date", installed_version="1.0.0"
            )
            result = runner.invoke(check)

    assert result.exit_code == 0
    assert "Installed version: 1.0.0" in result.output
    assert "up to date" in result.output


def test_check_command_version_mismatch(tmp_path: Path) -> None:
    """Test check command when versions mismatch."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        save_artifact_state(project_dir, ArtifactState(version="1.0.0"))

        with (
            patch(
                "erk.cli.commands.artifacts.check.get_current_version",
                return_value="2.0.0",
            ),
            patch("erk.cli.commands.artifacts.check.check_staleness") as mock_check,
        ):
            mock_check.return_value = MagicMock(
                is_stale=True, reason="version mismatch", installed_version="1.0.0"
            )
            result = runner.invoke(check)

    assert result.exit_code == 0
    assert "version mismatch" in result.output


def test_check_command_dev_mode(tmp_path: Path) -> None:
    """Test check command in dev mode."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        (project_dir / "packages" / "erk-kits").mkdir(parents=True)

        with patch(
            "erk.cli.commands.artifacts.check.get_current_version", return_value="1.0.0"
        ):
            result = runner.invoke(check)

    assert result.exit_code == 0
    assert "Dev mode: True" in result.output


def test_sync_command_dev_mode(tmp_path: Path) -> None:
    """Test sync command in dev mode does nothing."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        (project_dir / "packages" / "erk-kits").mkdir(parents=True)

        result = runner.invoke(sync)

    assert result.exit_code == 0
    assert "Dev mode" in result.output
    assert "nothing to sync" in result.output


def test_sync_command_up_to_date(tmp_path: Path) -> None:
    """Test sync command when already up to date."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        save_artifact_state(project_dir, ArtifactState(version="1.0.0"))

        with patch(
            "erk.cli.commands.artifacts.sync.check_staleness"
        ) as mock_check:
            mock_check.return_value = MagicMock(is_stale=False)
            result = runner.invoke(sync)

    assert result.exit_code == 0
    assert "up to date" in result.output


def test_sync_command_force_flag(tmp_path: Path) -> None:
    """Test sync command with --force flag syncs even when up to date."""
    runner = CliRunner()

    mock_sync_result = MagicMock()
    mock_sync_result.artifacts_installed = 3
    mock_sync_result.hooks_installed = 1

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        save_artifact_state(project_dir, ArtifactState(version="1.0.0"))

        with patch(
            "erk.cli.commands.artifacts.sync.sync_artifacts",
            return_value=mock_sync_result,
        ):
            result = runner.invoke(sync, ["--force"])

    assert result.exit_code == 0
    assert "Synced 3 artifacts" in result.output


def test_sync_command_when_stale(tmp_path: Path) -> None:
    """Test sync command when artifacts are stale."""
    runner = CliRunner()

    mock_sync_result = MagicMock()
    mock_sync_result.artifacts_installed = 5
    mock_sync_result.hooks_installed = 2

    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        save_artifact_state(project_dir, ArtifactState(version="1.0.0"))

        with (
            patch("erk.cli.commands.artifacts.sync.check_staleness") as mock_check,
            patch(
                "erk.cli.commands.artifacts.sync.sync_artifacts",
                return_value=mock_sync_result,
            ),
        ):
            mock_check.return_value = MagicMock(is_stale=True)
            result = runner.invoke(sync)

    assert result.exit_code == 0
    assert "Synced 5 artifacts, 2 hooks" in result.output
