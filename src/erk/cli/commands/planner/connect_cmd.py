"""Connect to a planner box."""

import os

import click

from erk.core.context import ErkContext


@click.command("connect")
@click.argument("name", required=False)
@click.option("--ssh", is_flag=True, help="Connect via SSH instead of VS Code")
@click.pass_obj
def connect_planner(ctx: ErkContext, name: str | None, ssh: bool) -> None:
    """Connect to a planner box.

    If NAME is provided, connects to that planner. Otherwise, connects
    to the default planner.

    By default, opens VS Code desktop to prevent idle timeout. Use --ssh
    to connect via SSH and launch Claude directly.
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

    if ssh:
        # Connect via gh codespace ssh with claude command
        click.echo(f"Connecting to planner '{planner.name}' via SSH...", err=True)

        # Replace current process with ssh session
        # -t: Force pseudo-terminal allocation (required for interactive TUI like claude)
        # bash -l -c: Use login shell to ensure PATH is set up (claude installs to ~/.claude/local/)
        # Launch Claude in interactive mode for planning workflows
        #
        # IMPORTANT: The entire remote command (bash -l -c '...') must be a single argument.
        # SSH concatenates command arguments with spaces without preserving grouping.
        # If passed as separate args ["bash", "-l", "-c", "cmd"], the remote receives:
        #   bash -l -c git pull && uv sync && ...
        # Instead of:
        #   bash -l -c "git pull && uv sync && ..."
        # This causes `bash -l -c git` to run `git` with no subcommand (exits with help).
        setup_commands = "git pull && uv sync && source .venv/bin/activate"
        claude_command = "claude --allow-dangerously-skip-permissions --verbose"
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
    else:
        # Default: Open VS Code desktop (prevents idle timeout)
        click.echo("Opening VS Code...", err=True)
        click.echo("", err=True)
        click.echo("Run in VS Code terminal:", err=True)
        click.echo("  git pull && uv sync && source .venv/bin/activate", err=True)
        click.echo(
            "  claude --allow-dangerously-skip-permissions --verbose",
            err=True,
        )

        os.execvp("gh", ["gh", "codespace", "code", "-c", planner.gh_name])
