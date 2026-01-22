"""Tests for objective next-plan command.

Note: The next-plan command uses os.execvp() which replaces the process.
These tests verify behavior up to (but not including) the execvp call,
and test error paths which don't reach execvp.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig, InteractiveClaudeConfig


def test_next_plan_shows_error_when_claude_not_installed() -> None:
    """Test next-plan shows error when Claude CLI is not installed."""
    runner = CliRunner()

    with patch("shutil.which", return_value=None):
        result = runner.invoke(cli, ["objective", "next-plan", "123"])

    assert result.exit_code == 1
    assert "Claude CLI not found" in result.output


def test_next_plan_launches_claude_with_issue_number() -> None:
    """Test next-plan launches Claude with the correct command for issue number.

    The next-plan command uses plan mode since it's for creating implementation plans.
    """
    runner = CliRunner()

    with (
        patch("shutil.which", return_value="/usr/local/bin/claude"),
        patch("os.execvp") as mock_execvp,
    ):
        runner.invoke(cli, ["objective", "next-plan", "3679"])

    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "claude"
    args_list = call_args[0][1]
    # Uses plan mode since this is for creating implementation plans
    assert args_list == [
        "claude",
        "--permission-mode",
        "plan",
        "/erk:objective-next-plan 3679",
    ]


def test_next_plan_launches_claude_with_url() -> None:
    """Test next-plan launches Claude with the correct command for GitHub URL."""
    runner = CliRunner()
    url = "https://github.com/owner/repo/issues/3679"

    with (
        patch("shutil.which", return_value="/usr/local/bin/claude"),
        patch("os.execvp") as mock_execvp,
    ):
        runner.invoke(cli, ["objective", "next-plan", url])

    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "claude"
    args_list = call_args[0][1]
    # Uses plan mode since this is for creating implementation plans
    assert args_list == [
        "claude",
        "--permission-mode",
        "plan",
        f"/erk:objective-next-plan {url}",
    ]


def test_next_plan_alias_np_works() -> None:
    """Test that 'np' alias works for next-plan command."""
    runner = CliRunner()

    with (
        patch("shutil.which", return_value="/usr/local/bin/claude"),
        patch("os.execvp") as mock_execvp,
    ):
        runner.invoke(cli, ["objective", "np", "123"])

    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "claude"
    assert "/erk:objective-next-plan 123" in call_args[0][1]


def test_next_plan_requires_issue_ref_argument() -> None:
    """Test next-plan requires ISSUE_REF argument."""
    runner = CliRunner()

    result = runner.invoke(cli, ["objective", "next-plan"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_next_plan_respects_allow_dangerous_config() -> None:
    """Test that allow_dangerous from config is passed to Claude CLI.

    When the user has allow_dangerous = true in their ~/.erk/config.toml,
    the --allow-dangerously-skip-permissions flag should be passed to Claude.
    """
    runner = CliRunner()

    # Create a context with allow_dangerous enabled in interactive_claude config
    ic_config = InteractiveClaudeConfig(
        model=None,
        verbose=False,
        permission_mode="acceptEdits",
        dangerous=False,
        allow_dangerous=True,
    )
    global_config = GlobalConfig.test(
        erk_root=Path("/tmp/erk"),
        interactive_claude=ic_config,
    )
    ctx = context_for_test(global_config=global_config)

    with (
        patch("shutil.which", return_value="/usr/local/bin/claude"),
        patch("os.execvp") as mock_execvp,
    ):
        runner.invoke(cli, ["objective", "next-plan", "123"], obj=ctx)

    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    args_list = call_args[0][1]
    # Should include --allow-dangerously-skip-permissions from config
    # and use plan mode (overridden from default acceptEdits)
    assert args_list == [
        "claude",
        "--permission-mode",
        "plan",
        "--allow-dangerously-skip-permissions",
        "/erk:objective-next-plan 123",
    ]
