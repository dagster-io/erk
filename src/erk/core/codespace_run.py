"""Codespace remote execution helper.

Builds shell commands for streaming execution on codespaces.
Every remoteable command calls this with its own erk CLI string.
"""

import shlex


def build_codespace_ssh_command(
    erk_command: str,
    *,
    working_directory: str | None = None,
) -> str:
    """Wrap an erk CLI command for streaming codespace execution.

    Produces a bash command that:
    1. Optionally cd to working_directory
    2. Bootstraps the environment (git pull, uv sync, activate venv)
    3. Runs the given erk command in the foreground, streaming output

    Args:
        erk_command: The erk CLI command to run remotely (e.g., "erk objective plan 42")
        working_directory: Remote directory to cd into before running commands, or None

    Returns:
        A shell string suitable for passing to codespace SSH
    """
    cd_prefix = f"cd {shlex.quote(working_directory)} && " if working_directory is not None else ""
    bootstrap = "git pull && uv sync && source .venv/bin/activate"
    return f"bash -l -c '{cd_prefix}{bootstrap} && {erk_command}'"
