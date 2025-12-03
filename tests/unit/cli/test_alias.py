"""Tests for CLI command alias functionality."""

import click
from click.testing import CliRunner

from erk.cli.alias import ALIAS_ATTR, alias, get_aliases, register_with_aliases
from erk.cli.help_formatter import ErkCommandGroup


def test_alias_decorator_stores_single_alias() -> None:
    """The @alias decorator stores a single alias on the command."""

    @alias("co")
    @click.command("checkout")
    def my_command() -> None:
        pass

    assert hasattr(my_command, ALIAS_ATTR)
    assert getattr(my_command, ALIAS_ATTR) == ["co"]


def test_alias_decorator_stores_multiple_aliases() -> None:
    """The @alias decorator stores multiple aliases on the command."""

    @alias("ls", "l")
    @click.command("list")
    def my_command() -> None:
        pass

    assert getattr(my_command, ALIAS_ATTR) == ["ls", "l"]


def test_get_aliases_returns_empty_for_undecorated_command() -> None:
    """get_aliases returns empty list for commands without @alias decorator."""

    @click.command("status")
    def my_command() -> None:
        pass

    result = get_aliases(my_command)
    assert result == []


def test_get_aliases_returns_aliases_for_decorated_command() -> None:
    """get_aliases returns the list of aliases for decorated commands."""

    @alias("co")
    @click.command("checkout")
    def my_command() -> None:
        pass

    result = get_aliases(my_command)
    assert result == ["co"]


def test_register_with_aliases_registers_primary_and_aliases() -> None:
    """register_with_aliases registers both the primary command and its aliases."""

    @click.group()
    def cli() -> None:
        pass

    @alias("co")
    @click.command("checkout")
    def checkout_cmd() -> None:
        click.echo("checkout executed")

    register_with_aliases(cli, checkout_cmd)

    # Both "checkout" and "co" should be registered
    assert "checkout" in cli.commands
    assert "co" in cli.commands

    # Both should point to the same command
    assert cli.commands["checkout"] is cli.commands["co"]


def test_register_with_aliases_with_explicit_name() -> None:
    """register_with_aliases uses explicit name when provided."""

    @click.group()
    def cli() -> None:
        pass

    @alias("ls")
    @click.command("list_plans")
    def list_cmd() -> None:
        click.echo("list executed")

    register_with_aliases(cli, list_cmd, name="list")

    # Should be registered as "list" not "list_plans"
    assert "list" in cli.commands
    assert "ls" in cli.commands
    assert "list_plans" not in cli.commands


def test_register_with_aliases_without_aliases() -> None:
    """register_with_aliases works correctly for commands without aliases."""

    @click.group()
    def cli() -> None:
        pass

    @click.command("status")
    def status_cmd() -> None:
        click.echo("status executed")

    register_with_aliases(cli, status_cmd)

    assert "status" in cli.commands
    # No extra commands should be added
    assert len(cli.commands) == 1


def test_alias_command_is_invocable() -> None:
    """Commands registered via alias can be invoked."""
    runner = CliRunner()

    @click.group()
    def cli() -> None:
        pass

    @alias("co")
    @click.command("checkout")
    def checkout_cmd() -> None:
        click.echo("checkout executed")

    register_with_aliases(cli, checkout_cmd)

    # Test primary command
    result = runner.invoke(cli, ["checkout"])
    assert result.exit_code == 0
    assert "checkout executed" in result.output

    # Test alias
    result = runner.invoke(cli, ["co"])
    assert result.exit_code == 0
    assert "checkout executed" in result.output


def test_help_formatter_shows_aliases_inline() -> None:
    """ErkCommandGroup shows aliases inline with primary command in help."""
    runner = CliRunner()

    @click.group(cls=ErkCommandGroup)
    def cli() -> None:
        pass

    @alias("co")
    @click.command("checkout")
    def checkout_cmd() -> None:
        """Checkout a branch."""

    register_with_aliases(cli, checkout_cmd)

    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0

    # Should show "checkout (co)" format
    assert "checkout (co)" in result.output


def test_help_formatter_hides_alias_as_separate_entry() -> None:
    """ErkCommandGroup hides aliases from showing as separate commands."""
    runner = CliRunner()

    @click.group(cls=ErkCommandGroup)
    def cli() -> None:
        pass

    @alias("ls")
    @click.command("list")
    def list_cmd() -> None:
        """List items."""

    register_with_aliases(cli, list_cmd)

    result = runner.invoke(cli, ["--help"])

    # Count occurrences - "list" and "ls" should appear together once
    # not as separate entries
    lines = result.output.split("\n")
    list_lines = [line for line in lines if "list" in line.lower() and "ls" in line.lower()]
    separate_ls_lines = [
        line
        for line in lines
        if line.strip().startswith("ls ")  # Would indicate separate "ls" command
    ]

    assert len(list_lines) >= 1  # Should have at least one "list / ls" line
    assert len(separate_ls_lines) == 0  # Should not have separate "ls" entry
