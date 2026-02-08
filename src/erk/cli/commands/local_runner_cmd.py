"""CLI commands for managing local plan implementation runners."""

import subprocess

import click

from erk_shared.output.output import user_output


@click.group("local-runner")
def local_runner() -> None:
    """Manage local plan implementation runners."""


@local_runner.command()
def status() -> None:
    """List active local implementation sessions."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        user_output("No active tmux sessions")
        return

    sessions = [line for line in result.stdout.splitlines() if line.startswith("erk-impl-")]

    if not sessions:
        user_output("No active local implementations")
        return

    user_output("Active local implementations:")
    for session in sessions:
        issue_number = session.replace("erk-impl-", "")
        user_output(f"  - Issue #{issue_number} (session: {session})")


@local_runner.command()
@click.argument("issue_number", type=int)
def logs(issue_number: int) -> None:
    """Attach to tmux session for a running implementation."""
    session_name = f"erk-impl-{issue_number}"

    # Check if session exists
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        capture_output=True,
    )

    if result.returncode != 0:
        msg = f"No active session for issue #{issue_number}"
        user_output(click.style("Error: ", fg="red") + msg)
        return

    # Attach to session (this replaces the current process)
    subprocess.run(["tmux", "attach", "-t", session_name])


@local_runner.command()
@click.argument("issue_number", type=int)
def stop(issue_number: int) -> None:
    """Stop a running local implementation."""
    session_name = f"erk-impl-{issue_number}"

    result = subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        capture_output=True,
    )

    if result.returncode == 0:
        user_output(f"Stopped implementation for issue #{issue_number}")
    else:
        msg = f"No active session for issue #{issue_number}"
        user_output(click.style("Error: ", fg="red") + msg)
