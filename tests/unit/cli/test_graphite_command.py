"""Tests for GraphiteCommand, GraphiteCommandWithHiddenOptions, and GraphiteGroup."""

from pathlib import Path

import click
from click.testing import CliRunner

from erk.cli.graphite_command import (
    GraphiteCommand,
    GraphiteCommandWithHiddenOptions,
    GraphiteGroup,
)
from erk.cli.help_formatter import (
    ErkCommandGroup,
    _requires_graphite,
    script_option,
)
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite

# --- Helper function tests ---


def test_requires_graphite_returns_true_for_graphite_command() -> None:
    """_requires_graphite returns True for GraphiteCommand instances."""

    @click.command("test-cmd", cls=GraphiteCommand)
    def test_cmd() -> None:
        """Test command."""

    assert _requires_graphite(test_cmd) is True


def test_requires_graphite_returns_true_for_graphite_command_with_hidden_options() -> None:
    """_requires_graphite returns True for GraphiteCommandWithHiddenOptions instances."""

    @click.command("test-cmd", cls=GraphiteCommandWithHiddenOptions)
    @script_option
    def test_cmd(script: bool) -> None:
        """Test command."""

    assert _requires_graphite(test_cmd) is True


def test_requires_graphite_returns_true_for_graphite_group() -> None:
    """_requires_graphite returns True for GraphiteGroup instances."""

    @click.group("test-group", cls=GraphiteGroup)
    def test_group() -> None:
        """Test group."""

    assert _requires_graphite(test_group) is True


def test_requires_graphite_returns_false_for_regular_command() -> None:
    """_requires_graphite returns False for regular Click commands."""

    @click.command("test-cmd")
    def test_cmd() -> None:
        """Test command."""

    assert _requires_graphite(test_cmd) is False


def test_requires_graphite_returns_false_for_regular_group() -> None:
    """_requires_graphite returns False for regular Click groups."""

    @click.group("test-group")
    def test_group() -> None:
        """Test group."""

    assert _requires_graphite(test_group) is False


# --- Invoke behavior tests ---


def test_graphite_command_invoke_checks_graphite_availability() -> None:
    """GraphiteCommand.invoke() calls Ensure.graphite_available() before command."""

    @click.command("test-cmd", cls=GraphiteCommand)
    @click.pass_obj
    def test_cmd(ctx: object) -> None:
        """Test command."""
        click.echo("Command executed")

    runner = CliRunner()

    # Create context with GraphiteDisabled sentinel
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED),
    )

    result = runner.invoke(test_cmd, [], obj=ctx, catch_exceptions=False)

    # Should fail with Graphite disabled error
    assert result.exit_code == 1
    assert "requires Graphite to be enabled" in result.output


def test_graphite_command_invoke_succeeds_with_graphite_enabled() -> None:
    """GraphiteCommand.invoke() succeeds when Graphite is available."""

    @click.command("test-cmd", cls=GraphiteCommand)
    @click.pass_obj
    def test_cmd(ctx: object) -> None:
        """Test command."""
        click.echo("Command executed successfully")

    runner = CliRunner()

    # Create context with real FakeGraphite (Graphite is available)
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=True,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=FakeGraphite(),
    )

    result = runner.invoke(test_cmd, [], obj=ctx, catch_exceptions=False)

    # Should succeed
    assert result.exit_code == 0
    assert "Command executed successfully" in result.output


def test_graphite_command_with_hidden_options_invoke_checks_graphite_availability() -> None:
    """GraphiteCommandWithHiddenOptions.invoke() calls Ensure.graphite_available()."""

    @click.command("test-cmd", cls=GraphiteCommandWithHiddenOptions)
    @script_option
    @click.pass_obj
    def test_cmd(ctx: object, script: bool) -> None:
        """Test command with hidden options."""
        click.echo("Command executed")

    runner = CliRunner()

    # Create context with GraphiteDisabled sentinel
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED),
    )

    result = runner.invoke(test_cmd, [], obj=ctx, catch_exceptions=False)

    # Should fail with Graphite not installed error
    assert result.exit_code == 1
    assert "requires Graphite to be installed" in result.output


def test_graphite_command_with_hidden_options_preserves_hidden_options_behavior() -> None:
    """GraphiteCommandWithHiddenOptions still shows hidden options when config enabled."""

    @click.command("test-cmd", cls=GraphiteCommandWithHiddenOptions)
    @script_option
    @click.pass_obj
    def test_cmd(ctx: object, script: bool) -> None:
        """Test command with hidden options."""
        click.echo(f"Script mode: {script}")

    runner = CliRunner()

    # Create context with show_hidden_commands=True and Graphite enabled
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=True,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=True,
        ),
        graphite=FakeGraphite(),
    )

    # Request help
    result = runner.invoke(test_cmd, ["--help"], obj=ctx, catch_exceptions=False)

    # Should show Hidden Options section
    assert result.exit_code == 0
    assert "Hidden Options:" in result.output
    assert "--script" in result.output


def test_graphite_command_invoke_handles_none_ctx_obj() -> None:
    """GraphiteCommand.invoke() handles ctx.obj being None gracefully."""

    @click.command("test-cmd", cls=GraphiteCommand)
    def test_cmd() -> None:
        """Test command without context object."""
        click.echo("Command executed")

    runner = CliRunner()

    # Invoke without obj (ctx.obj will be None)
    result = runner.invoke(test_cmd, [], catch_exceptions=False)

    # Should succeed - no Graphite check when ctx.obj is None
    assert result.exit_code == 0
    assert "Command executed" in result.output


# --- Dynamic hiding tests ---


def test_graphite_command_hidden_in_help_when_graphite_unavailable() -> None:
    """GraphiteCommand is hidden from help when Graphite is unavailable."""

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        """Test CLI."""

    @cli.command("graphite-cmd", cls=GraphiteCommand)
    def graphite_cmd() -> None:
        """This requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Create context with Graphite disabled
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED),
    )

    result = runner.invoke(cli, ["--help"], obj=ctx, catch_exceptions=False)

    # Regular command should be visible
    assert "regular-cmd" in result.output
    assert "This is a regular command" in result.output

    # Graphite command should be hidden
    assert "graphite-cmd" not in result.output


def test_graphite_command_visible_in_help_when_graphite_available() -> None:
    """GraphiteCommand is visible in help when Graphite is available."""

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        """Test CLI."""

    @cli.command("graphite-cmd", cls=GraphiteCommand)
    def graphite_cmd() -> None:
        """This requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Create context with Graphite enabled
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=True,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=FakeGraphite(),
    )

    result = runner.invoke(cli, ["--help"], obj=ctx, catch_exceptions=False)

    # Both commands should be visible
    assert "regular-cmd" in result.output
    assert "graphite-cmd" in result.output
    assert "This requires Graphite" in result.output


def test_graphite_group_hidden_in_help_when_graphite_unavailable() -> None:
    """GraphiteGroup is hidden from help when Graphite is unavailable."""

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        """Test CLI."""

    @cli.group("graphite-group", cls=GraphiteGroup)
    def graphite_group() -> None:
        """This group requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Create context with Graphite disabled
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED),
    )

    result = runner.invoke(cli, ["--help"], obj=ctx, catch_exceptions=False)

    # Regular command should be visible
    assert "regular-cmd" in result.output

    # Graphite group should be hidden
    assert "graphite-group" not in result.output


def test_graphite_group_visible_in_help_when_graphite_available() -> None:
    """GraphiteGroup is visible in help when Graphite is available."""

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        """Test CLI."""

    @cli.group("graphite-group", cls=GraphiteGroup)
    def graphite_group() -> None:
        """This group requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Create context with Graphite enabled
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=True,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
        ),
        graphite=FakeGraphite(),
    )

    result = runner.invoke(cli, ["--help"], obj=ctx, catch_exceptions=False)

    # Both should be visible
    assert "regular-cmd" in result.output
    assert "graphite-group" in result.output
    assert "This group requires Graphite" in result.output


def test_graphite_commands_shown_in_hidden_section_when_show_hidden_enabled() -> None:
    """Graphite commands appear in Hidden section when show_hidden is enabled."""

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    @click.pass_context
    def cli(ctx: click.Context) -> None:
        """Test CLI."""

    @cli.command("graphite-cmd", cls=GraphiteCommand)
    def graphite_cmd() -> None:
        """This requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Create context with Graphite disabled but show_hidden enabled
    ctx = context_for_test(
        global_config=GlobalConfig(
            erk_root=Path("/tmp/erks"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            show_hidden_commands=True,
        ),
        graphite=GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED),
    )

    result = runner.invoke(cli, ["--help"], obj=ctx, catch_exceptions=False)

    # Regular command should be visible
    assert "regular-cmd" in result.output

    # Graphite command should be in Hidden section
    assert "Hidden:" in result.output
    assert "graphite-cmd" in result.output


# --- Real command tests (verify actual commands use the pattern) ---


def test_real_up_command_is_graphite_command() -> None:
    """Verify the real 'up' command uses GraphiteCommandWithHiddenOptions."""
    from erk.cli.commands.up import up_cmd

    assert _requires_graphite(up_cmd)


def test_real_down_command_is_graphite_command() -> None:
    """Verify the real 'down' command uses GraphiteCommandWithHiddenOptions."""
    from erk.cli.commands.down import down_cmd

    assert _requires_graphite(down_cmd)


def test_real_list_stack_command_is_graphite_command() -> None:
    """Verify the real 'stack list' command uses GraphiteCommand."""
    from erk.cli.commands.stack.list_cmd import list_stack

    assert _requires_graphite(list_stack)


def test_real_checkout_command_is_graphite_command() -> None:
    """Verify the real 'checkout' command uses GraphiteCommand."""
    from erk.cli.commands.branch.checkout_cmd import branch_checkout

    assert _requires_graphite(branch_checkout)


def test_real_auto_restack_command_is_graphite_command() -> None:
    """Verify the real 'auto-restack' command uses GraphiteCommand."""
    from erk.cli.commands.pr.auto_restack_cmd import pr_auto_restack

    assert _requires_graphite(pr_auto_restack)


def test_real_stack_group_is_graphite_group() -> None:
    """Verify the real 'stack' group uses GraphiteGroup."""
    from erk.cli.commands.stack import stack_group

    assert _requires_graphite(stack_group)
