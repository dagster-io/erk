"""Unit tests for dispatch_learn_workflow exec script.

Tests for the `erk exec dispatch-learn-workflow` command which dispatches
the learn-extract-dispatch workflow on GitHub.
"""

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.dispatch_learn_workflow import (
    dispatch_learn_workflow,
)


def test_dispatch_learn_workflow_requires_plan_issue() -> None:
    """Test that --plan-issue is required."""
    runner = CliRunner()

    result = runner.invoke(
        dispatch_learn_workflow,
        ["--pr-number=456"],
    )

    assert result.exit_code == 2
    assert "Missing option '--plan-issue'" in result.output


def test_dispatch_learn_workflow_requires_pr_number() -> None:
    """Test that --pr-number is required."""
    runner = CliRunner()

    result = runner.invoke(
        dispatch_learn_workflow,
        ["--plan-issue=123"],
    )

    assert result.exit_code == 2
    assert "Missing option '--pr-number'" in result.output


def test_dispatch_learn_workflow_command_registered() -> None:
    """Test that dispatch-learn-workflow command is registered in exec group."""
    from erk.cli.commands.exec.group import exec_group

    command_names = [cmd.name for cmd in exec_group.commands.values()]
    assert "dispatch-learn-workflow" in command_names


def test_dispatch_learn_workflow_accepts_gist_url() -> None:
    """Test that --gist-url option is accepted."""
    runner = CliRunner()

    # Will fail because gh is not available, but should not fail because
    # of unrecognized option
    result = runner.invoke(
        dispatch_learn_workflow,
        [
            "--plan-issue=123",
            "--pr-number=456",
            "--gist-url=https://gist.github.com/abc123",
        ],
    )

    assert "no such option: --gist-url" not in result.output.lower()


def test_dispatch_learn_workflow_accepts_auto_implement() -> None:
    """Test that --auto-implement flag is accepted."""
    runner = CliRunner()

    # Will fail because gh is not available, but should not fail because
    # of unrecognized option
    result = runner.invoke(
        dispatch_learn_workflow,
        [
            "--plan-issue=123",
            "--pr-number=456",
            "--auto-implement",
        ],
    )

    assert "no such option: --auto-implement" not in result.output.lower()
