"""Tests for GraphiteCommand, GraphiteCommandWithHiddenOptions, and GraphiteGroup."""

from pathlib import Path

import click
from click.testing import CliRunner
from pytest import MonkeyPatch

from erk.cli import help_formatter as help_formatter_module
from erk.cli.graphite_command import (
    GraphiteCommand,
    GraphiteCommandWithHiddenOptions,
    GraphiteGroup,
)
from erk.cli.help_formatter import (
    ErkCommandGroup,
    _is_graphite_available,
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


# --- _is_graphite_available helper tests ---


def test_is_graphite_available_returns_true_when_ctx_obj_has_real_graphite() -> None:
    """_is_graphite_available returns True when ctx.obj.graphite is not disabled."""
    ctx = context_for_test(graphite=FakeGraphite())

    # Create a Click context with our ErkContext as obj
    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = ctx

    assert _is_graphite_available(click_ctx) is True


def test_is_graphite_available_returns_false_when_ctx_obj_has_disabled_graphite() -> None:
    """_is_graphite_available returns False when ctx.obj.graphite is GraphiteDisabled."""
    ctx = context_for_test(graphite=GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED))

    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = ctx

    assert _is_graphite_available(click_ctx) is False


def test_is_graphite_available_falls_back_to_config_when_ctx_obj_is_none(
    monkeypatch: MonkeyPatch,
) -> None:
    """_is_graphite_available reads config from disk when ctx.obj is None.

    This tests the scenario where --help is shown before the CLI callback runs,
    so ctx.obj is still None. The function should fall back to reading the
    config store and checking if gt is installed.
    """
    # Create a mock config store that returns use_graphite=True
    mock_config = GlobalConfig(
        erk_root=Path("/tmp/erks"),
        use_graphite=True,
        shell_setup_complete=True,
        github_planning=True,
    )

    class MockErkInstallation:
        def config_exists(self) -> bool:
            return True

        def load_config(self) -> GlobalConfig:
            return mock_config

    # Monkeypatch RealErkInstallation to return our mock
    monkeypatch.setattr(help_formatter_module, "RealErkInstallation", MockErkInstallation)

    # Monkeypatch shutil.which to simulate gt being installed
    monkeypatch.setattr(help_formatter_module.shutil, "which", lambda cmd: "/usr/bin/gt")

    # Create a Click context with obj=None (simulating help before callback)
    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = None

    assert _is_graphite_available(click_ctx) is True


def test_is_graphite_available_returns_false_when_config_disabled_and_ctx_obj_none(
    monkeypatch: MonkeyPatch,
) -> None:
    """_is_graphite_available returns False when config has use_graphite=False."""
    mock_config = GlobalConfig(
        erk_root=Path("/tmp/erks"),
        use_graphite=False,
        shell_setup_complete=True,
        github_planning=True,
    )

    class MockErkInstallation:
        def config_exists(self) -> bool:
            return True

        def load_config(self) -> GlobalConfig:
            return mock_config

    monkeypatch.setattr(help_formatter_module, "RealErkInstallation", MockErkInstallation)

    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = None

    assert _is_graphite_available(click_ctx) is False


def test_is_graphite_available_returns_false_when_gt_not_installed_and_ctx_obj_none(
    monkeypatch: MonkeyPatch,
) -> None:
    """_is_graphite_available returns False when use_graphite=True but gt not installed."""
    mock_config = GlobalConfig(
        erk_root=Path("/tmp/erks"),
        use_graphite=True,
        shell_setup_complete=True,
        github_planning=True,
    )

    class MockErkInstallation:
        def config_exists(self) -> bool:
            return True

        def load_config(self) -> GlobalConfig:
            return mock_config

    monkeypatch.setattr(help_formatter_module, "RealErkInstallation", MockErkInstallation)
    # gt is not installed
    monkeypatch.setattr(help_formatter_module.shutil, "which", lambda cmd: None)

    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = None

    assert _is_graphite_available(click_ctx) is False


def test_is_graphite_available_returns_false_when_no_config_and_ctx_obj_none(
    monkeypatch: MonkeyPatch,
) -> None:
    """_is_graphite_available returns False when no config exists and ctx.obj is None."""

    class MockMissingErkInstallation:
        def config_exists(self) -> bool:
            return False

        def load_config(self) -> GlobalConfig:
            raise FileNotFoundError("No config")

    monkeypatch.setattr(help_formatter_module, "RealErkInstallation", MockMissingErkInstallation)

    click_ctx = click.Context(click.Command("test"))
    click_ctx.obj = None

    assert _is_graphite_available(click_ctx) is False


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


def test_graphite_command_visible_when_help_shown_without_ctx_obj(
    monkeypatch: MonkeyPatch,
) -> None:
    """Graphite commands visible in help even when ctx.obj is None.

    This tests the critical scenario where --help is processed before the
    CLI callback runs (Click's eager option handling), so ctx.obj is None.
    The format_commands method should fall back to reading config from disk.

    This test would have caught the bug where Graphite commands were hidden
    when use_graphite=True but help was shown before callback set ctx.obj.
    """
    # Create a mock config store that returns use_graphite=True
    mock_config = GlobalConfig(
        erk_root=Path("/tmp/erks"),
        use_graphite=True,
        shell_setup_complete=True,
        github_planning=True,
    )

    class MockErkInstallation:
        def config_exists(self) -> bool:
            return True

        def load_config(self) -> GlobalConfig:
            return mock_config

    # Monkeypatch at the module level where it's used
    monkeypatch.setattr(help_formatter_module, "RealErkInstallation", MockErkInstallation)
    monkeypatch.setattr(help_formatter_module.shutil, "which", lambda cmd: "/usr/bin/gt")

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    def cli() -> None:
        """Test CLI."""
        # Note: No ctx.obj is set - simulating help before callback

    @cli.command("graphite-cmd", cls=GraphiteCommand)
    def graphite_cmd() -> None:
        """This requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Invoke WITHOUT passing obj - this simulates help being shown before
    # the CLI callback runs (which is what happens with Click's eager --help)
    result = runner.invoke(cli, ["--help"], catch_exceptions=False)

    # Both commands should be visible (Graphite command should NOT be hidden)
    assert "regular-cmd" in result.output
    assert "graphite-cmd" in result.output
    assert "This requires Graphite" in result.output


def test_graphite_command_hidden_when_help_shown_without_ctx_obj_and_config_disabled(
    monkeypatch: MonkeyPatch,
) -> None:
    """Graphite commands hidden in help when use_graphite=False and ctx.obj is None."""
    mock_config = GlobalConfig(
        erk_root=Path("/tmp/erks"),
        use_graphite=False,
        shell_setup_complete=True,
        github_planning=True,
    )

    class MockErkInstallation:
        def config_exists(self) -> bool:
            return True

        def load_config(self) -> GlobalConfig:
            return mock_config

    monkeypatch.setattr(help_formatter_module, "RealErkInstallation", MockErkInstallation)

    @click.group("cli", cls=ErkCommandGroup, grouped=False)
    def cli() -> None:
        """Test CLI."""

    @cli.command("graphite-cmd", cls=GraphiteCommand)
    def graphite_cmd() -> None:
        """This requires Graphite."""

    @cli.command("regular-cmd")
    def regular_cmd() -> None:
        """This is a regular command."""

    runner = CliRunner()

    # Invoke WITHOUT passing obj
    result = runner.invoke(cli, ["--help"], catch_exceptions=False)

    # Regular command visible, Graphite command hidden
    assert "regular-cmd" in result.output
    assert "graphite-cmd" not in result.output


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


def test_real_stack_group_is_graphite_group() -> None:
    """Verify the real 'stack' group uses GraphiteGroup."""
    from erk.cli.commands.stack import stack_group

    assert _requires_graphite(stack_group)
