"""Command alias decorator for CLI commands."""

from collections.abc import Callable
from typing import TypeVar

import click

F = TypeVar("F", bound=click.Command)
C = TypeVar("C", bound=Callable[..., object])

# Store alias metadata on command objects
ALIAS_ATTR = "_erk_aliases"


def alias(*names: str) -> Callable[[F], F]:
    """Decorator to declare aliases for a Click command.

    Must be applied BEFORE @click.command (i.e., listed above it in the decorator stack).
    This is because decorators are applied bottom-to-top, so @alias runs AFTER @click.command
    creates the Command object.

    Usage:
        @alias("co")
        @click.command("checkout")
        def checkout_cmd(...):
            ...
    """

    def decorator(cmd: F) -> F:
        existing = getattr(cmd, ALIAS_ATTR, [])
        setattr(cmd, ALIAS_ATTR, existing + list(names))
        return cmd

    return decorator


def get_aliases(cmd: click.Command) -> list[str]:
    """Get aliases declared on a command."""
    return getattr(cmd, ALIAS_ATTR, [])


def register_with_aliases(group: click.Group, cmd: click.Command, name: str | None = None) -> None:
    """Register a command and its declared aliases with a group.

    Args:
        group: The Click group to register the command with
        cmd: The command to register
        name: Optional explicit name (defaults to cmd.name)
    """
    cmd_name = name or cmd.name
    group.add_command(cmd, name=cmd_name)
    for alias_name in get_aliases(cmd):
        group.add_command(cmd, name=alias_name)
