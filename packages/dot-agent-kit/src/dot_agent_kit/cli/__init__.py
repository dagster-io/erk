import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.context import create_context
from dot_agent_kit.version import __version__

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class LazyGroup(click.Group):
    """Click Group that lazily loads commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._commands_registered = False

    def list_commands(self, ctx):
        """List available commands, registering them if needed."""
        if not self._commands_registered:
            self._register_commands()
        return super().list_commands(ctx)

    def get_command(self, ctx, cmd_name):
        """Get a command by name, registering if needed."""
        if not self._commands_registered:
            self._register_commands()
        return super().get_command(ctx, cmd_name)

    def _register_commands(self) -> None:
        """Register all commands with the CLI group."""
        if self._commands_registered:
            return

        from dot_agent_kit.commands import check
        from dot_agent_kit.commands.artifact.group import artifact_group
        from dot_agent_kit.commands.command import command
        from dot_agent_kit.commands.docs.group import docs_group
        from dot_agent_kit.commands.hook.group import hook_group
        from dot_agent_kit.commands.init import init
        from dot_agent_kit.commands.kit.group import kit_group
        from dot_agent_kit.commands.kit_command.group import kit_command_group
        from dot_agent_kit.commands.md.group import md_group
        from dot_agent_kit.commands.status import st, status

        self.add_command(check.check)
        self.add_command(command)
        self.add_command(init)
        self.add_command(status)
        self.add_command(st)

        # Register command groups
        self.add_command(artifact_group)
        self.add_command(docs_group)
        self.add_command(hook_group)
        self.add_command(kit_group)
        self.add_command(kit_command_group)
        self.add_command(md_group)

        # Add 'run' as an alias for 'kit-command' for backwards compatibility
        # Users can use either 'dot-agent run' or 'dot-agent kit-command'
        run_alias = click.Group(
            name="run",
            help="(Alias for kit-command) Run kit cli commands from bundled kits.",
            commands=kit_command_group.commands,
        )
        self.add_command(run_alias)

        self._commands_registered = True


@click.command(cls=LazyGroup, invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True, help="Show full stack traces for errors")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Manage Claude Code kits."""
    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = create_context(debug=debug)

    if ctx.invoked_subcommand is None:
        user_output(ctx.get_help())


def main() -> None:
    """Entry point with error boundary."""
    from dot_agent_kit.error_boundary import cli_error_boundary

    cli_error_boundary(cli)()


if __name__ == "__main__":
    main()
