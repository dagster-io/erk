"""Custom Click help formatter for organized command display."""

import click

from erk.cli.alias import get_aliases


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
                with formatter.section("Deprecated (Hidden)"):
                    self._format_command_list(ctx, formatter, hidden_commands)
            return

        # Grouped output mode - organize into sections
        # Define command organization (aliases now derived from decorator, not hardcoded)
        core_navigation = ["checkout", "up", "down"]
        command_groups = ["wt", "plan", "stack", "run", "admin", "config", "completion"]
        top_level_plans = ["dash", "implement", "submit"]
        initialization = ["init"]

        # Categorize commands
        core_cmds = []
        group_cmds = []
        plan_cmds = []
        init_cmds = []
        other_cmds = []

        for name, cmd in commands:
            # Skip aliases (they'll be shown with their primary command)
            if name in alias_map:
                continue

            if name in core_navigation:
                core_cmds.append((name, cmd))
            elif name in command_groups:
                group_cmds.append((name, cmd))
            elif name in top_level_plans:
                plan_cmds.append((name, cmd))
            elif name in initialization:
                init_cmds.append((name, cmd))
            else:
                # Other commands
                other_cmds.append((name, cmd))

        # Format sections
        if plan_cmds:
            with formatter.section("Plans"):
                self._format_command_list(ctx, formatter, plan_cmds)

        if core_cmds:
            with formatter.section("Core Navigation"):
                self._format_command_list(ctx, formatter, core_cmds)

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
            with formatter.section("Deprecated (Hidden)"):
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
