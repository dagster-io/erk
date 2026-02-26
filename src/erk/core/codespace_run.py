"""Codespace remote execution helper.

Builds shell commands for streaming execution on codespaces.
Every remoteable command calls this with its own erk CLI string.
"""

import re


def _sanitize_tmux_session_name(name: str) -> str:
    """Sanitize a string for use as a tmux session name.

    Replaces non-alphanumeric characters (except hyphens) with hyphens,
    collapses consecutive hyphens, and strips leading/trailing hyphens.
    """
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-")


def build_codespace_ssh_command(erk_command: str) -> str:
    """Wrap an erk CLI command for streaming codespace execution.

    Produces a bash command that:
    1. Bootstraps the environment (git pull, uv sync, activate venv)
    2. Runs the given erk command in the foreground, streaming output

    Args:
        erk_command: The erk CLI command to run remotely (e.g., "erk objective plan 42")

    Returns:
        A shell string suitable for passing to codespace SSH
    """
    return f"bash -l -c 'git pull && uv sync && source .venv/bin/activate && {erk_command}'"


def build_codespace_tmux_command(erk_command: str, *, session_name: str) -> str:
    """Wrap an erk CLI command in a tmux session for codespace execution.

    Produces a bash command that:
    1. Bootstraps the environment (git pull, uv sync, activate venv)
    2. Runs the given erk command inside a tmux session

    The tmux ``-A`` flag means:
    - First run: creates the session and runs the command
    - Reconnect: attaches to the existing session (command arg is ignored)

    Bootstrap runs outside tmux so reconnects are fast.

    Args:
        erk_command: The erk CLI command to run remotely (e.g., "erk objective plan 42")
        session_name: Human-readable session name (will be sanitized for tmux)

    Returns:
        A shell string suitable for passing to codespace SSH
    """
    safe_name = _sanitize_tmux_session_name(session_name)
    tmux_cmd = f"tmux new-session -A -s {safe_name} {erk_command}"
    return build_codespace_ssh_command(tmux_cmd)
