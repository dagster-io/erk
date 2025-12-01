"""Connect to a planner box."""

import os

import click

from erk.core.context import ErkContext


@click.command("connect")
@click.argument("name", required=False)
@click.pass_obj
def connect_planner(ctx: ErkContext, name: str | None) -> None:
    """Connect to a planner box and launch Claude.

    If NAME is provided, connects to that planner. Otherwise, connects
    to the default planner.

    This replaces the current process with an SSH session to the
    codespace running Claude.
    """
    # Get planner by name or default
    if name is not None:
        planner = ctx.planner_registry.get(name)
        if planner is None:
            click.echo(f"Error: No planner named '{name}' found.", err=True)
            click.echo("\nUse 'erk planner list' to see registered planners.", err=True)
            raise SystemExit(1)
    else:
        planner = ctx.planner_registry.get_default()
        if planner is None:
            default_name = ctx.planner_registry.get_default_name()
            if default_name is not None:
                click.echo(f"Error: Default planner '{default_name}' not found.", err=True)
            else:
                click.echo("Error: No default planner set.", err=True)
            click.echo("\nUse 'erk planner list' to see registered planners.", err=True)
            click.echo("Use 'erk planner set-default <name>' to set a default.", err=True)
            raise SystemExit(1)

    # Check if configured
    if not planner.configured:
        click.echo(f"Warning: Planner '{planner.name}' has not been configured yet.", err=True)
        click.echo(f"Run 'erk planner configure {planner.name}' for initial setup.", err=True)

    # Update last connected timestamp
    ctx.planner_registry.update_last_connected(planner.name, ctx.time.now())

    # Connect via gh codespace ssh with claude command
    click.echo(f"Connecting to planner '{planner.name}'...", err=True)

    # Replace current process with ssh session
    # -t: Force pseudo-terminal allocation (required for interactive TUI like claude)
    # bash -l -c: Use login shell to ensure PATH is set up (claude installs to ~/.claude/local/)
    # Pass /erk:craft-plan as initial prompt to launch the planning workflow immediately
    #
    # IMPORTANT: The entire remote command (bash -l -c '...') must be a single argument.
    # SSH concatenates command arguments with spaces without preserving grouping.
    # If passed as separate args ["bash", "-l", "-c", "cmd"], the remote receives:
    #   bash -l -c git pull && uv sync && ...
    # Instead of:
    #   bash -l -c "git pull && uv sync && ..."
    # This causes `bash -l -c git` to run `git` with no subcommand (exits with help).
    setup_commands = "git pull && uv sync && source .venv/bin/activate"
    claude_command = 'claude "/erk:craft-plan"'
    remote_command = f"bash -l -c '{setup_commands} && {claude_command}'"

    os.execvp(
        "gh",
        [
            "gh",
            "codespace",
            "ssh",
            "-c",
            planner.gh_name,
            "--",
            "-t",
            remote_command,
        ],
    )
