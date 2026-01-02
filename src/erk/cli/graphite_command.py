"""Custom Click command classes that require Graphite integration.

This module provides declarative command classes that automatically:
1. Check Graphite availability before command execution
2. Are hidden from help output when Graphite is unavailable

Usage:
    @click.command("list", cls=GraphiteCommand)
    def list_stack(ctx: ErkContext) -> None:
        # No need for Ensure.graphite_available(ctx) - handled by GraphiteCommand
        ...

    @click.command("up", cls=GraphiteCommandWithHiddenOptions)
    @script_option
    def up_cmd(ctx: ErkContext, script: bool) -> None:
        # Combines Graphite check with hidden options support
        ...

    @click.group("stack", cls=GraphiteGroup)
    def stack_group() -> None:
        # Entire group hidden when Graphite unavailable
        ...
"""

from typing import Any

import click

from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions


class GraphiteCommand(click.Command):
    """Command that requires Graphite integration.

    Automatically checks Graphite availability before command execution.
    When Graphite is unavailable, this command is hidden from help output
    but can still be invoked directly (failing with a helpful error message).

    Use this class for commands that depend on Graphite functionality
    but don't need hidden options support.
    """

    def invoke(self, ctx: click.Context) -> Any:
        """Invoke command after validating Graphite availability."""
        if ctx.obj is not None:
            Ensure.graphite_available(ctx.obj)
        return super().invoke(ctx)


class GraphiteCommandWithHiddenOptions(CommandWithHiddenOptions):
    """GraphiteCommand + hidden options support.

    Combines the Graphite availability check from GraphiteCommand
    with the hidden options formatting from CommandWithHiddenOptions.

    Use this class for commands that:
    1. Require Graphite functionality
    2. Have hidden options (like --script)
    """

    def invoke(self, ctx: click.Context) -> Any:
        """Invoke command after validating Graphite availability."""
        if ctx.obj is not None:
            Ensure.graphite_available(ctx.obj)
        return super().invoke(ctx)


class GraphiteGroup(click.Group):
    """Group that requires Graphite integration.

    When used with cls=GraphiteGroup, the entire command group is hidden
    from help output when Graphite is unavailable. Commands within the
    group can still be invoked directly and will fail with helpful error
    messages via their own GraphiteCommand classes.

    The hiding logic is implemented in ErkCommandGroup.format_commands().
    """

    pass
