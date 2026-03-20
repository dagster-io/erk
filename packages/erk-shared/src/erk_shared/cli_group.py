"""Custom Click group for organized command display."""

import shutil
from typing import Any, cast

import click

from erk_shared.cli_alias import get_aliases
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from erk_shared.gateway.graphite.disabled import GraphiteDisabled

# Type names for Graphite-requiring commands (checked by string to avoid circular imports)
_GRAPHITE_COMMAND_TYPES = frozenset(
    {
        "GraphiteCommand",
        "GraphiteCommandWithHiddenOptions",
        "GraphiteGroup",
    }
)


def _requires_graphite(cmd: click.Command) -> bool:
    """Check if a command requires Graphite integration.

    Uses class name matching to avoid circular imports with graphite_command.py.
    """
    return type(cmd).__name__ in _GRAPHITE_COMMAND_TYPES


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
    installation = RealErkInstallation()
    if installation.config_exists():
        return installation.load_config().show_hidden_commands
    return False


def _set_ctx_show_hidden(ctx: click.Context, value: bool) -> None:
    """Set show_hidden attribute on Click context.

    Click's Context allows dynamic attributes at runtime (documented API behavior).
    We use cast(Any, ...) to bypass type stubs that don't include dynamic attrs.
    """
    cast(Any, ctx).show_hidden = value


def _is_graphite_available(ctx: click.Context) -> bool:
    """Check if Graphite is available for command visibility.

    Checks ctx.obj.graphite if available (tests or after callback),
    otherwise loads config from disk and checks gt binary (help before callback).
    """
    if ctx.obj is not None:
        return not isinstance(ctx.obj.graphite, GraphiteDisabled)
    # Fallback to loading from disk (for help before callback runs)
    installation = RealErkInstallation()
    if installation.config_exists():
        config = installation.load_config()
        if config.use_graphite:
            # Config says use Graphite - check if gt is installed
            return shutil.which("gt") is not None
    return False


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
        super().__init__(**cast(dict[str, Any], kwargs))
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
        """
        # If ctx.obj is provided (tests or already-created context), use its config
        if ctx.obj is not None:
            config = getattr(ctx.obj, "global_config", None)
            if config is not None and getattr(config, "show_hidden_commands", False):
                _set_ctx_show_hidden(ctx, value=True)
            return

        # Otherwise try to load config directly from disk
        installation = RealErkInstallation()
        if installation.config_exists():
            config = installation.load_config()
            if config.show_hidden_commands:
                _set_ctx_show_hidden(ctx, value=True)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format commands into organized sections or flat list."""
        show_hidden = getattr(ctx, "show_hidden", False)

        # Check if Graphite is available (for hiding Graphite-dependent commands)
        graphite_available = _is_graphite_available(ctx)

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

            # Commands are effectively hidden if:
            # 1. They have hidden=True, OR
            # 2. They require Graphite and Graphite is unavailable
            effectively_hidden = cmd.hidden or (_requires_graphite(cmd) and not graphite_available)

            if effectively_hidden:
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
            "land",
            "launch",
            "list",
            "one-shot",
            "release-notes",
            "up",
            "upgrade",
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
            "md",
            "objective",
            "plan",
            "pr",
            "project",
            "run",
            "slot",
            "stack",
            "workflow",
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
