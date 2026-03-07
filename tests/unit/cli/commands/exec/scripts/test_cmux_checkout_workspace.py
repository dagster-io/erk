"""Tests for cmux-open-pr exec script."""

import json
from unittest import mock

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.cmux_checkout_workspace import cmux_open_pr


def test_cmux_open_pr_success_with_branch() -> None:
    """cmux-open-pr succeeds when branch is provided."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="workspace-12345\n",
            stderr="",
        )

        result = runner.invoke(
            cmux_open_pr,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 8152
    assert output["branch"] == "my-branch"
    assert output["workspace_name"] == "workspace-12345"


def test_cmux_open_pr_success_auto_detect_branch() -> None:
    """cmux-open-pr auto-detects branch when not provided."""
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
            cmux_open_pr,
            ["--pr", "8152"],
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 8152
    assert output["branch"] == "feature-branch"


def test_cmux_open_pr_fails_auto_detect() -> None:
    """cmux-open-pr fails gracefully when branch auto-detection fails."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout="",
            stderr="error",
        )

        result = runner.invoke(
            cmux_open_pr,
            ["--pr", "8152"],
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to detect head branch" in output["error"]


def test_cmux_open_pr_fails_cmux_command() -> None:
    """cmux-open-pr fails when cmux pipeline fails."""
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
            cmux_open_pr,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to create cmux workspace" in output["error"]


def test_cmux_open_pr_teleport_mode() -> None:
    """cmux-open-pr --mode teleport uses teleport command."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="workspace-12345\n",
            stderr="",
        )

        result = runner.invoke(
            cmux_open_pr,
            ["--pr", "8152", "--branch", "my-branch", "--mode", "teleport"],
        )

    assert result.exit_code == 0
    # Verify the teleport command was used in the shell pipeline
    shell_cmd = mock_run.call_args_list[0][0][0][2]  # bash -c <cmd>
    assert "erk pr teleport" in shell_cmd
    assert "--new-slot --script --sync" in shell_cmd


def test_cmux_open_pr_default_mode_uses_checkout() -> None:
    """cmux-open-pr default mode uses checkout command."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="workspace-12345\n",
            stderr="",
        )

        result = runner.invoke(
            cmux_open_pr,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 0
    # Verify the checkout command was used in the shell pipeline
    shell_cmd = mock_run.call_args_list[0][0][0][2]  # bash -c <cmd>
    assert "erk pr checkout" in shell_cmd
    assert "--script" in shell_cmd
    assert "teleport" not in shell_cmd


def test_cmux_open_pr_extracts_workspace_name() -> None:
    """cmux-open-pr correctly extracts workspace name from output."""
    runner = CliRunner()

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="Created workspace: my-workspace\n",
            stderr="",
        )

        result = runner.invoke(
            cmux_open_pr,
            ["--pr", "8152", "--branch", "my-branch"],
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["workspace_name"] == "my-workspace"
