"""Codespace remote execution helper.

Builds shell commands for streaming execution on codespaces.
Every remoteable command calls this with its own erk CLI string.
"""


def build_codespace_ssh_command(erk_command: str) -> str:
    """Wrap an erk CLI command for streaming codespace execution.

    Produces a bash command that:
    1. Bootstraps the environment (git pull, uv sync, activate venv)
    2. Runs the given erk command in the foreground, streaming output

    Args:
        erk_command: The erk CLI command to run remotely (e.g., "erk objective implement 42")

    Returns:
        A shell string suitable for passing to codespace SSH
    """
    return f"bash -l -c 'git pull && uv sync && source .venv/bin/activate && {erk_command}'"
