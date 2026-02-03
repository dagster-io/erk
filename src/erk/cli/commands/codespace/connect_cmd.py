"""Connect to a codespace and launch Claude."""

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.context import ErkContext


@click.command("connect")
@click.argument("name", required=False)
@click.option("--shell", is_flag=True, help="Drop into shell instead of launching Claude.")
@click.pass_obj
def connect_codespace(ctx: ErkContext, name: str | None, *, shell: bool) -> None:
    """Connect to a codespace and launch Claude.

    If NAME is provided, connects to that codespace. Otherwise, connects
    to the default codespace.

    Connects via SSH and launches Claude with --dangerously-skip-permissions
    since codespace isolation provides safety.

    Use --shell to drop into an interactive shell instead of launching Claude.
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)

    click.echo(f"Connecting to codespace '{codespace.name}'...", err=True)

    # Connect via SSH and launch Claude (or shell with --shell flag)
    # -t: Force pseudo-terminal allocation (required for interactive TUI like claude)
    # bash -l -c: Use login shell to ensure PATH is set up (claude installs to ~/.claude/local/)
    #
    # IMPORTANT: The entire remote command (bash -l -c '...') must be a single argument.
    # SSH concatenates command arguments with spaces without preserving grouping.
    if shell:
        remote_command = "bash -l"
    else:
        setup_commands = "git pull && uv sync && source .venv/bin/activate"
        claude_command = "claude --dangerously-skip-permissions"
        remote_command = f"bash -l -c '{setup_commands} && {claude_command}'"

    # Replace current process with SSH session to codespace
    ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_command)
