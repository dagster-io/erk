"""Tests for cmux-sync-workspace exec script."""

import json
from unittest import mock

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.cmux_sync_workspace import cmux_sync_workspace


def test_cmux_sync_workspace_success_with_branch() -> None:
    """cmux-sync-workspace succeeds when branch is provided."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="workspace-12345\n",
            stderr="",
        )

        result = runner.invoke(
            cmux_sync_workspace,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 8152
    assert output["branch"] == "my-branch"
    assert output["workspace_name"] == "workspace-12345"


def test_cmux_sync_workspace_success_auto_detect_branch() -> None:
    """cmux-sync-workspace auto-detects branch when not provided."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        # First call: gh pr view to get branch
        # Second call: cmux pipeline
        mock_run.side_effect = [
            mock.Mock(
                returncode=0,
                stdout="feature-branch\n",
                stderr="",
            ),
            mock.Mock(
                returncode=0,
                stdout="workspace-99999\n",
                stderr="",
            ),
        ]

        result = runner.invoke(
            cmux_sync_workspace,
            ["--pr", "8152"],
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 8152
    assert output["branch"] == "feature-branch"


def test_cmux_sync_workspace_fails_auto_detect() -> None:
    """cmux-sync-workspace fails gracefully when branch auto-detection fails."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout="",
            stderr="error",
        )

        result = runner.invoke(
            cmux_sync_workspace,
            ["--pr", "8152"],
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to detect head branch" in output["error"]


def test_cmux_sync_workspace_fails_cmux_command() -> None:
    """cmux-sync-workspace fails when cmux pipeline fails."""
    import subprocess

    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        # Simulate subprocess.run with check=True raising CalledProcessError
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["bash", "-c", "..."],
            stderr="cmux error: workspace already exists",
        )
        mock_run.side_effect = error

        result = runner.invoke(
            cmux_sync_workspace,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to create cmux workspace" in output["error"]


def test_cmux_sync_workspace_extracts_workspace_name() -> None:
    """cmux-sync-workspace correctly extracts workspace name from output."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="Created workspace: my-workspace\n",
            stderr="",
        )

        result = runner.invoke(
            cmux_sync_workspace,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["workspace_name"] == "my-workspace"
