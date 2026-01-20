"""Connect to a codespace and launch Claude."""

import os

import click

from erk.core.context import ErkContext


@click.command("connect")
@click.argument("name", required=False)
@click.pass_obj
def connect_codespace(ctx: ErkContext, name: str | None) -> None:
    """Connect to a codespace and launch Claude.

    If NAME is provided, connects to that codespace. Otherwise, connects
    to the default codespace.

    Connects via SSH and launches Claude with --dangerously-skip-permissions
    since codespace isolation provides safety.
    """
    # Get codespace by name or default
    if name is not None:
        codespace = ctx.codespace_registry.get(name)
        if codespace is None:
            click.echo(f"Error: No codespace named '{name}' found.", err=True)
            click.echo("\nUse 'erk codespace setup' to create one.", err=True)
            raise SystemExit(1)
    else:
        codespace = ctx.codespace_registry.get_default()
        if codespace is None:
            default_name = ctx.codespace_registry.get_default_name()
            if default_name is not None:
                click.echo(f"Error: Default codespace '{default_name}' not found.", err=True)
            else:
                click.echo("Error: No default codespace set.", err=True)
            click.echo("\nUse 'erk codespace setup' to create one.", err=True)
            raise SystemExit(1)

    click.echo(f"Connecting to codespace '{codespace.name}'...", err=True)

    # Connect via SSH and launch Claude
    # -t: Force pseudo-terminal allocation (required for interactive TUI like claude)
    # bash -l -c: Use login shell to ensure PATH is set up (claude installs to ~/.claude/local/)
    #
    # IMPORTANT: The entire remote command (bash -l -c '...') must be a single argument.
    # SSH concatenates command arguments with spaces without preserving grouping.
    setup_commands = "git pull && uv sync && source .venv/bin/activate"
    claude_command = "claude --dangerously-skip-permissions"
    remote_command = f"bash -l -c '{setup_commands} && {claude_command}'"

    # GH-API-AUDIT: REST - codespace SSH connection
    os.execvp(
        "gh",
        [
            "gh",
            "codespace",
            "ssh",
            "-c",
            codespace.gh_name,
            "--",
            "-t",
            remote_command,
        ],
    )
