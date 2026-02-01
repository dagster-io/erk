"""Codespace remote execution helper.

Builds shell commands for fire-and-forget execution on codespaces.
Every remoteable command calls this with its own erk CLI string.
"""


def build_codespace_run_command(erk_command: str) -> str:
    """Wrap an erk CLI command for fire-and-forget codespace execution.

    Produces a bash command that:
    1. Bootstraps the environment (git pull, uv sync, activate venv)
    2. Runs the given erk command via nohup in the background
    3. Redirects output to /tmp/erk-run.log

    Args:
        erk_command: The erk CLI command to run remotely (e.g., "erk objective next-plan 42")

    Returns:
        A shell string suitable for passing to codespace SSH
    """
    setup = "git pull && uv sync && source .venv/bin/activate"
    return f"bash -l -c '{setup} && nohup {erk_command} > /tmp/erk-run.log 2>&1 &'"
