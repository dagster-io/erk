"""Tests for objective next-plan command.

Note: The next-plan command uses ClaudeLauncher.launch_interactive() which
replaces the process. These tests verify behavior up to (but not including)
the process replacement, using FakeClaudeLauncher to track calls.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig, InteractiveClaudeConfig
from erk_shared.gateway.claude_launcher.fake import FakeClaudeLauncher


def test_next_plan_shows_error_when_claude_not_installed() -> None:
    """Test next-plan shows error when Claude CLI is not installed."""
    runner = CliRunner()

    launcher = FakeClaudeLauncher(
        launch_error="Claude CLI not found\nInstall from: https://claude.com/download"
    )
    ctx = context_for_test(claude_launcher=launcher)

    result = runner.invoke(cli, ["objective", "next-plan", "123"], obj=ctx)

    assert result.exit_code == 1
    assert "Claude CLI not found" in result.output


def test_next_plan_launches_claude_with_issue_number() -> None:
    """Test next-plan launches Claude with the correct command for issue number.

    The next-plan command uses plan mode since it's for creating implementation plans.
    """
    runner = CliRunner()
    fake_launcher = FakeClaudeLauncher()
    ctx = context_for_test(claude_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "next-plan", "3679"], obj=ctx)

    # FakeClaudeLauncher.launch_interactive raises SystemExit(0), which CliRunner catches
    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == "/erk:objective-next-plan 3679"
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.config.allow_dangerous is False
    assert fake_launcher.last_call.config.dangerous is False


def test_next_plan_launches_claude_with_url() -> None:
    """Test next-plan launches Claude with the correct command for GitHub URL."""
    runner = CliRunner()
    url = "https://github.com/owner/repo/issues/3679"
    fake_launcher = FakeClaudeLauncher()
    ctx = context_for_test(claude_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "next-plan", url], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == f"/erk:objective-next-plan {url}"
    assert fake_launcher.last_call.config.permission_mode == "plan"


def test_next_plan_alias_np_works() -> None:
    """Test that 'np' alias works for next-plan command."""
    runner = CliRunner()
    fake_launcher = FakeClaudeLauncher()
    ctx = context_for_test(claude_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "np", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == "/erk:objective-next-plan 123"


def test_next_plan_requires_issue_ref_argument() -> None:
    """Test next-plan requires ISSUE_REF argument."""
    runner = CliRunner()

    result = runner.invoke(cli, ["objective", "next-plan"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_next_plan_respects_allow_dangerous_config() -> None:
    """Test that allow_dangerous from config is passed to Claude launcher.

    When the user has allow_dangerous = true in their ~/.erk/config.toml,
    the config object passed to the launcher should have allow_dangerous=True.
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
    fake_launcher = FakeClaudeLauncher()
    ctx = context_for_test(global_config=global_config, claude_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "next-plan", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Should include allow_dangerous from config
    # and use plan mode (overridden from default acceptEdits)
    assert fake_launcher.last_call.config.allow_dangerous is True
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.command == "/erk:objective-next-plan 123"


def test_next_plan_with_dangerous_flag() -> None:
    """Test that -d/--dangerous flag enables allow_dangerous in launcher config."""
    runner = CliRunner()
    fake_launcher = FakeClaudeLauncher()
    ctx = context_for_test(claude_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "next-plan", "-d", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Should include allow_dangerous from -d flag
    assert fake_launcher.last_call.config.allow_dangerous is True
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.command == "/erk:objective-next-plan 123"


def test_next_plan_without_dangerous_flag() -> None:
    """Test that without -d flag, allow_dangerous is not enabled."""
    runner = CliRunner()
    fake_launcher = FakeClaudeLauncher()
    ctx = context_for_test(claude_launcher=fake_launcher)

    result = runner.invoke(cli, ["objective", "next-plan", "123"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    # Should NOT include allow_dangerous
    assert fake_launcher.last_call.config.allow_dangerous is False
    assert fake_launcher.last_call.config.permission_mode == "plan"
    assert fake_launcher.last_call.command == "/erk:objective-next-plan 123"
