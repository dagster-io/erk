"""Tests for erk plan replan command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.agent_launcher.fake import FakeAgentLauncher


def test_replan_launches_agent_with_plan_mode() -> None:
    """Test that replan launches agent in plan mode with correct command."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["plan", "replan", "2521"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == "/erk:replan 2521"
    assert fake_launcher.last_call.config.permission_mode == "plan"


def test_replan_with_multiple_issue_refs() -> None:
    """Test that replan passes multiple issue refs to command."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["plan", "replan", "123", "456", "789"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == "/erk:replan 123 456 789"
    assert fake_launcher.last_call.config.permission_mode == "plan"


def test_replan_requires_issue_ref_argument() -> None:
    """Test that replan requires at least one ISSUE_REF argument."""
    runner = CliRunner()

    result = runner.invoke(cli, ["plan", "replan"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_replan_shows_error_when_agent_not_installed() -> None:
    """Test that replan shows error when agent CLI is not installed."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher(
        launch_error="Claude CLI not found\nInstall from: https://claude.com/download"
    )
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["plan", "replan", "2521"], obj=ctx)

    assert result.exit_code == 1
    assert "Claude CLI not found" in result.output
