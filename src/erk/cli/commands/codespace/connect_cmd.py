"""Connect to a codespace and launch Claude."""

import os
import shlex

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.context import ErkContext


def _build_export_prefix(env_vars: tuple[str, ...]) -> str:
    """Parse --env KEY=VALUE args and return an export prefix string.

    Returns empty string if no env vars provided, otherwise returns
    'export K1=V1 K2=V2 && ' ready to prepend to a command.
    """
    if not env_vars:
        return ""

    parts: list[str] = []
    for env_var in env_vars:
        if "=" not in env_var:
            click.echo(f"Error: Invalid --env format: {env_var!r} (expected KEY=VALUE)", err=True)
            raise SystemExit(1)
        key, value = env_var.split("=", 1)
        parts.append(f"{key}={shlex.quote(value)}")

    return f"export {' '.join(parts)} && "


def _tty_session_name() -> str:
    """Derive a tmux session name from the local terminal's TTY device.

    Each terminal tab/window has a unique TTY path (e.g., /dev/ttys003 on macOS,
    /dev/pts/3 on Linux). Using this as the session name means the same terminal
    always reconnects to the same remote session, while different terminals get
    independent sessions.
    """
    try:
        tty_path = os.ttyname(0)  # e.g., /dev/ttys003 or /dev/pts/3
        suffix = tty_path.removeprefix("/dev/").replace("/", "-")
        return f"claude-{suffix}"
    except OSError:
        return "claude"


@click.command("connect")
@click.argument("name", required=False)
@click.option("--shell", is_flag=True, help="Drop into shell instead of launching Claude.")
@click.option(
    "--tmux",
    "-t",
    is_flag=True,
    help="Wrap Claude in a tmux session for persistence across disconnects.",
)
@click.option(
    "--session",
    "session_name",
    default=None,
    help="tmux session name (implies --tmux; default: derived from local TTY).",
)
@click.option("--env", "env_vars", multiple=True, help="Set env var in remote session (KEY=VALUE).")
@click.pass_obj
def connect_codespace(
    ctx: ErkContext,
    name: str | None,
    *,
    shell: bool,
    tmux: bool,
    session_name: str | None,
    env_vars: tuple[str, ...],
) -> None:
    """Connect to a codespace and launch Claude.

    If NAME is provided, connects to that codespace. Otherwise, connects
    to the default codespace.

    Connects via SSH and launches Claude with --dangerously-skip-permissions
    since codespace isolation provides safety.

    Use --shell to drop into an interactive shell instead of launching Claude.
    Use --tmux/-t to wrap Claude in a persistent tmux session.
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)

    # --session implies --tmux
    use_tmux = tmux or session_name is not None

    export_prefix = _build_export_prefix(env_vars)

    # Connect via SSH and launch Claude (or shell with --shell flag)
    # -t: Force pseudo-terminal allocation (required for interactive TUI like claude)
    # bash -l -c: Use login shell to ensure PATH is set up (claude installs to ~/.claude/local/)
    #
    # IMPORTANT: The entire remote command (bash -l -c '...') must be a single argument.
    # SSH concatenates command arguments with spaces without preserving grouping.
    if shell:
        if export_prefix:
            remote_command = f"bash -l -c '{export_prefix}exec bash -l'"
        else:
            remote_command = "bash -l"
        click.echo(f"Connecting to codespace '{codespace.name}'...", err=True)
    else:
        setup_commands = "git pull && uv sync && source .venv/bin/activate"
        claude_command = "claude --dangerously-skip-permissions"

        if use_tmux:
            session = session_name if session_name is not None else _tty_session_name()
            # Force TERM to xterm-256color for tmux — remote may lack terminfo for local terminal (e.g. ghostty)
            claude_command = (
                f"TERM=xterm-256color tmux new-session -A -s {session} {claude_command}"
            )
            click.echo(
                f"Connecting to codespace '{codespace.name}' (tmux session: {session})...",
                err=True,
            )
        else:
            click.echo(f"Connecting to codespace '{codespace.name}'...", err=True)

        remote_command = f"bash -l -c '{export_prefix}{setup_commands} && {claude_command}'"

    # Replace current process with SSH session to codespace
    ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_command)
