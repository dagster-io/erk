"""Init command group for erk initialization and capability management."""

import click

from erk.cli.commands.init.capability import capability_group
from erk.cli.commands.init.main import run_init
from erk.cli.help_formatter import ErkCommandGroup
from erk.core.context import ErkContext


@click.group("init", cls=ErkCommandGroup, invoke_without_command=True)
@click.option("-f", "--force", is_flag=True, help="Overwrite existing repo config if present.")
@click.option(
    "--shell",
    is_flag=True,
    help="Show shell integration setup instructions (completion + auto-activation wrapper).",
)
@click.option(
    "--hooks",
    "hooks_only",
    is_flag=True,
    help="Only set up Claude Code hooks.",
)
@click.option(
    "--no-interactive",
    "no_interactive",
    is_flag=True,
    help="Skip all interactive prompts (gitignore, permissions, hooks, shell setup).",
)
@click.pass_context
def init_group(
    ctx: click.Context,
    *,
    force: bool,
    shell: bool,
    hooks_only: bool,
    no_interactive: bool,
) -> None:
    """Initialize erk for this repo and scaffold config.toml.

    When run without a subcommand, performs full initialization.
    Use 'erk init capability' subcommands to manage optional features.
    """
    if ctx.invoked_subcommand is None:
        # Run main init when no subcommand given
        erk_ctx: ErkContext = ctx.obj
        run_init(
            erk_ctx,
            force=force,
            shell=shell,
            hooks_only=hooks_only,
            no_interactive=no_interactive,
        )


# Register subcommands
init_group.add_command(capability_group)
