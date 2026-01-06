"""Switch request marker for seamless worktree switching.

This script writes marker files that signal the shell wrapper to switch
to a different worktree. When Claude terminates, the shell wrapper reads
these markers and restarts Claude in the target worktree.

Usage:
    erk exec switch-request <target> [--command <slash-command>]

The <target> is an issue number that will be passed to `erk implement`.
The optional --command specifies a slash command to run after switching.

Marker files:
    ~/.erk/switch-request           - Contains target issue number
    ~/.erk/switch-request-command   - Contains resume command (if provided)

Exit codes:
    0 = success (markers written)
    1 = error
"""

import json

import click

from erk_shared.context.helpers import require_erk_installation


def _output_json(success: bool, message: str) -> None:
    """Output JSON response."""
    click.echo(json.dumps({"success": success, "message": message}))


@click.command(name="switch-request")
@click.argument("target")
@click.option(
    "--command",
    "resume_command",
    help="Slash command to run after switching (e.g., /erk:plan-implement)",
)
@click.pass_context
def switch_request(ctx: click.Context, target: str, resume_command: str | None) -> None:
    """Write switch request markers for shell wrapper.

    TARGET is the issue number to implement (passed to `erk implement`).

    If --command is provided, that command will be passed to Claude
    as the resume command after switching to the new worktree.

    Examples:

    \b
      # Basic switch - wrapper will run: erk implement 123
      erk exec switch-request 123

    \b
      # With resume command - wrapper will run:
      #   1. erk implement 123 --path-only
      #   2. cd to worktree
      #   3. claude --continue /erk:plan-implement
      erk exec switch-request 123 --command /erk:plan-implement
    """
    installation = require_erk_installation(ctx)
    erk_root = installation.root()

    # Ensure ~/.erk/ exists
    if not erk_root.exists():
        erk_root.mkdir(parents=True, exist_ok=True)

    # Write switch-request marker
    switch_request_file = erk_root / "switch-request"
    switch_request_file.write_text(target, encoding="utf-8")

    # Write resume command if provided
    if resume_command is not None:
        command_file = erk_root / "switch-request-command"
        command_file.write_text(resume_command, encoding="utf-8")
        _output_json(True, f"Switch request created: {target} with command {resume_command}")
    else:
        # Remove any stale command file
        command_file = erk_root / "switch-request-command"
        if command_file.exists():
            command_file.unlink()
        _output_json(True, f"Switch request created: {target}")
