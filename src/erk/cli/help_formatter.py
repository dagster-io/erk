"""Custom Click help formatter for organized command display."""

from collections.abc import Callable
from typing import TypeVar

import click

from erk.cli.alias import get_aliases
from erk.core.config_store import RealConfigStore

F = TypeVar("F", bound=Callable[..., object])


def _get_show_hidden_from_context(ctx: click.Context) -> bool:
    """Check if hidden items should be shown based on config.

    Checks ctx.obj.global_config if available (tests),
    otherwise loads config from disk (direct CLI invocation).
    """
    if ctx.obj is not None:
        config = getattr(ctx.obj, "global_config", None)
        if config is not None:
            return bool(getattr(config, "show_hidden_commands", False))
    # Fallback to loading from disk
    store = RealConfigStore()
    if store.exists():
        return store.load().show_hidden_commands
    return False


class CommandWithHiddenOptions(click.Command):
    """Command that respects show_hidden_commands config for hidden options.

    Use this class for any command with hidden options (like --script).
    Hidden options are shown in a separate "Hidden Options" section when
    show_hidden_commands is enabled in config.
    """

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format options, showing hidden ones if config allows."""
        show_hidden = _get_show_hidden_from_context(ctx)

        opts = []
        hidden_opts = []
        for param in self.get_params(ctx):
            # Use getattr since only Option has 'hidden', not all Parameter types
            is_hidden = getattr(param, "hidden", False)

            if is_hidden:
                if show_hidden:
                    # Temporarily unhide to get help record (Click returns None for hidden)
                    param.hidden = False  # type: ignore[attr-defined]
                    rv = param.get_help_record(ctx)
                    param.hidden = True  # type: ignore[attr-defined]
                    if rv is not None:
                        hidden_opts.append(rv)
            else:
                rv = param.get_help_record(ctx)
                if rv is not None:
                    opts.append(rv)

        if opts:
            with formatter.section("Options"):
                formatter.write_dl(opts)

        if hidden_opts:
            with formatter.section("Hidden Options"):
                formatter.write_dl(hidden_opts)


def script_option(fn: F) -> F:
    """Decorator that adds --script option with proper settings.

    Must be applied to a function decorated with @click.command(cls=CommandWithHiddenOptions).
    The --script flag is hidden by default but visible when show_hidden_commands=True.

    Example:
        @click.command("up", cls=CommandWithHiddenOptions)
        @script_option
        def up_cmd(ctx: ErkContext, script: bool) -> None:
            ...
    """
    return click.option(
        "--script",
        is_flag=True,
        hidden=True,
        help="Output shell script for integration. NOT a dry run.",
    )(fn)


class ErkCommandGroup(click.Group):
    """Click Group that organizes commands into logical sections in help output.

    Commands are organized into sections based on their usage patterns:
    - Core Navigation: Primary workflow commands
    - Command Groups: Organized subcommands
    - Quick Access: Backward compatibility aliases

    Args:
        grouped: If True, organize commands into sections. If False, show flat list.
    """

    def __init__(self, grouped: bool = True, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.grouped = grouped

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format help output, setting show_hidden based on config first.

        This hook runs after context creation but before format_commands,
        allowing us to set ctx.show_hidden based on the global config.
        """
        # Set show_hidden based on config before formatting help
        self._set_show_hidden_from_context(ctx)

        # Call parent to format help (which will call format_commands)
        super().format_help(ctx, formatter)

    def _set_show_hidden_from_context(self, ctx: click.Context) -> None:
        """Set ctx.show_hidden based on config.

        Checks ctx.obj.global_config if available (tests),
        otherwise loads config from disk (direct CLI invocation).

        Note: Click's Context allows dynamic attributes at runtime.
        We use type: ignore since show_hidden isn't in Context's type stubs.
        """
        # If ctx.obj is provided (tests or already-created context), use its config
        if ctx.obj is not None:
            config = getattr(ctx.obj, "global_config", None)
            if config is not None and getattr(config, "show_hidden_commands", False):
                ctx.show_hidden = True  # type: ignore[attr-defined]
            return

        # Otherwise try to load config directly from disk
        store = RealConfigStore()
        if store.exists():
            config = store.load()
            if config.show_hidden_commands:
                ctx.show_hidden = True  # type: ignore[attr-defined]

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format commands into organized sections or flat list."""
        show_hidden = getattr(ctx, "show_hidden", False)

        commands = []
        hidden_commands = []
        # Build alias map: alias_name -> primary_name
        alias_map: dict[str, str] = {}

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue

            # Build alias map from decorator-declared aliases
            for alias_name in get_aliases(cmd):
                alias_map[alias_name] = subcommand

            if cmd.hidden:
                if show_hidden:
                    hidden_commands.append((subcommand, cmd))
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        # Flat output mode - single "Commands:" section
        if not self.grouped:
            # Filter out aliases (they'll be shown with their primary command)
            primary_commands = [(n, c) for n, c in commands if n not in alias_map]
            with formatter.section("Commands"):
                self._format_command_list(ctx, formatter, primary_commands)

            if hidden_commands:
                with formatter.section("Hidden"):
                    self._format_command_list(ctx, formatter, hidden_commands)
            return

        # Grouped output mode - organize into sections
        # Define command organization (aliases now derived from decorator, not hardcoded)
        top_level_commands = [
            "checkout",
            "dash",
            "delete",
            "doctor",
            "down",
            "implement",
            "list",
            "up",
        ]
        command_groups = [
            "admin",
            "artifact",
            "branch",
            "cc",
            "completion",
            "config",
            "docs",
            "hook",
            "info",
            "kit",
            "md",
            "objective",
            "plan",
            "planner",
            "pr",
            "project",
            "run",
            "stack",
            "wt",
        ]
        initialization = ["init"]

        # Categorize commands
        top_level_cmds = []
        group_cmds = []
        init_cmds = []
        other_cmds = []

        for name, cmd in commands:
            # Skip aliases (they'll be shown with their primary command)
            if name in alias_map:
                continue

            if name in top_level_commands:
                top_level_cmds.append((name, cmd))
            elif name in command_groups:
                group_cmds.append((name, cmd))
            elif name in initialization:
                init_cmds.append((name, cmd))
            else:
                # Other commands
                other_cmds.append((name, cmd))

        # Format sections
        if top_level_cmds:
            with formatter.section("Top-Level Commands"):
                self._format_command_list(ctx, formatter, top_level_cmds)

        if group_cmds:
            with formatter.section("Command Groups"):
                self._format_command_list(ctx, formatter, group_cmds)

        if init_cmds:
            with formatter.section("Initialization"):
                self._format_command_list(ctx, formatter, init_cmds)

        if other_cmds:
            with formatter.section("Other"):
                self._format_command_list(ctx, formatter, other_cmds)

        if hidden_commands:
            with formatter.section("Hidden"):
                self._format_command_list(ctx, formatter, hidden_commands)

    def _format_command_list(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
        commands: list[tuple[str, click.Command]],
    ) -> None:
        """Format a list of commands with their help text.

        Commands with aliases (declared via @alias decorator) are displayed
        as 'checkout (co)'.
        """
        rows = []
        for name, cmd in commands:
            # Get aliases for this command and format display name
            aliases = get_aliases(cmd)
            if aliases:
                display_name = f"{name} ({', '.join(aliases)})"
            else:
                display_name = name

            help_text = cmd.get_short_help_str(limit=formatter.width)
            rows.append((display_name, help_text))

        if rows:
            formatter.write_dl(rows)
