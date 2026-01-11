"""Launch Claude to create a plan from an objective step."""

import os
import shutil

import click

from erk.cli.alias import alias


@alias("np")
@click.command("next-plan")
@click.argument("issue_ref")
def next_plan(issue_ref: str) -> None:
    """Create an implementation plan from an objective step.

    ISSUE_REF is an objective issue number or GitHub URL.
    """
    # Verify Claude CLI is available
    if shutil.which("claude") is None:
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    # Build command with argument
    command = f"/erk:objective-next-plan {issue_ref}"

    # Build Claude CLI arguments
    cmd_args = ["claude", "--permission-mode", "acceptEdits", command]

    # Replace current process with Claude
    os.execvp("claude", cmd_args)
