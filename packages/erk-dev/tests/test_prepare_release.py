"""Tests for prepare_release command.

These tests verify:
- CLI command registration and basic invocation
- Validation logic for artifacts
- Workflow behavior patterns
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk_dev.cli import cli


def test_prepare_release_command_registered() -> None:
    """Verify prepare-release command is registered in CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["prepare-release", "--help"])

    assert result.exit_code == 0
    assert "Prepare a release" in result.output
    assert "--dry-run" in result.output


def test_prepare_release_fails_outside_repo_root(tmp_path: Path) -> None:
    """Test that prepare-release fails when not in repo root."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["prepare-release"])

    assert result.exit_code == 1
    assert "Not in repository root" in result.output


def test_prepare_release_dry_run_shows_banner() -> None:
    """Test that dry-run mode shows appropriate banner."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create minimal pyproject.toml
        Path("pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")

        with patch(
            "erk_dev.commands.prepare_release.command.get_workspace_packages"
        ) as mock_packages:
            mock_packages.side_effect = SystemExit(1)  # Stop early for this test

            result = runner.invoke(cli, ["prepare-release", "--dry-run"])

    assert "[DRY RUN MODE" in result.output
