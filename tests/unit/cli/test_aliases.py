"""Tests for CLI alias decorator and utilities."""

import click

from erk_shared.cli_alias import alias, get_aliases, register_with_aliases


def test_alias_decorator_adds_aliases_to_command() -> None:
    """@alias decorator attaches aliases to command."""

    @alias("co")
    @click.command("checkout")
    def checkout_cmd() -> None:
        pass

    assert get_aliases(checkout_cmd) == ["co"]


def test_alias_decorator_supports_multiple_aliases() -> None:
    """@alias decorator supports multiple aliases."""

    @alias("ls", "l")
    @click.command("list")
    def list_cmd() -> None:
        pass

    assert get_aliases(list_cmd) == ["ls", "l"]


def test_get_aliases_returns_empty_for_command_without_aliases() -> None:
    """get_aliases returns empty list for command without @alias."""

    @click.command("up")
    def up_cmd() -> None:
        pass

    assert get_aliases(up_cmd) == []


def test_register_with_aliases_adds_command_and_aliases() -> None:
    """register_with_aliases adds both canonical name and aliases."""

    @alias("co")
    @click.command("checkout")
    def checkout_cmd() -> None:
        pass

    group = click.Group()
    register_with_aliases(group, checkout_cmd)

    # Both canonical and alias should be registered
    assert "checkout" in group.commands
    assert "co" in group.commands
    # Both point to the same command
    assert group.commands["checkout"] is checkout_cmd
    assert group.commands["co"] is checkout_cmd


def test_register_with_aliases_with_explicit_name() -> None:
    """register_with_aliases respects explicit name parameter."""

    @alias("ls")
    @click.command("list_plans")
    def list_plans() -> None:
        pass

    group = click.Group()
    register_with_aliases(group, list_plans, name="list")

    # Should use explicit name, not cmd.name
    assert "list" in group.commands
    assert "ls" in group.commands
    assert "list_plans" not in group.commands


def test_register_with_aliases_without_aliases() -> None:
    """register_with_aliases works for commands without aliases."""

    @click.command("up")
    def up_cmd() -> None:
        pass

    group = click.Group()
    register_with_aliases(group, up_cmd)

    # Only canonical name should exist
    assert list(group.commands.keys()) == ["up"]
