"""Tests for erk pr address command (local variant)."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from tests.fakes.gateway.agent_launcher import FakeAgentLauncher
from tests.test_utils.test_context import context_for_test


def test_pr_address_launches_with_correct_command_and_permission_mode() -> None:
    """Test that address launches agent with /erk:pr-address command in edits mode."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["pr", "address"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.launch_called
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.command == "/erk:pr-address"
    assert fake_launcher.last_call.config.permission_mode == "edits"


def test_pr_address_dangerous_flag_sets_dangerous_true() -> None:
    """Test that --dangerous sets dangerous=True on config."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["pr", "address", "--dangerous"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.config.dangerous is True
    assert fake_launcher.last_call.config.permission_mode == "edits"


def test_pr_address_safe_flag_overrides_permission_mode() -> None:
    """Test that --safe overrides permission mode to safe."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["pr", "address", "--safe"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.config.permission_mode == "safe"


def test_pr_address_dangerous_and_safe_mutually_exclusive() -> None:
    """Test that --dangerous and --safe together produce an error."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["pr", "address", "--dangerous", "--safe"], obj=ctx)

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_pr_address_shows_error_when_agent_not_installed() -> None:
    """Test that address shows error when agent CLI is not installed."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher(
        launch_error="Claude CLI not found\nInstall from: https://claude.com/download"
    )
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["pr", "address"], obj=ctx)

    assert result.exit_code == 1
    assert "Claude CLI not found" in result.output


def test_pr_address_default_allows_dangerous_when_live_dangerously() -> None:
    """Test that default mode sets allow_dangerous=True when live_dangerously is true."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(agent_launcher=fake_launcher)

    result = runner.invoke(cli, ["pr", "address"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.config.allow_dangerous is True


def test_pr_address_default_no_allow_dangerous_when_live_dangerously_false() -> None:
    """Test that allow_dangerous is not set when live_dangerously=False."""
    runner = CliRunner()
    fake_launcher = FakeAgentLauncher()
    ctx = context_for_test(
        agent_launcher=fake_launcher,
        global_config=GlobalConfig.test(Path("/test/erks"), live_dangerously=False),
    )

    result = runner.invoke(cli, ["pr", "address"], obj=ctx)

    assert result.exit_code == 0
    assert fake_launcher.last_call is not None
    assert fake_launcher.last_call.config.allow_dangerous is False
