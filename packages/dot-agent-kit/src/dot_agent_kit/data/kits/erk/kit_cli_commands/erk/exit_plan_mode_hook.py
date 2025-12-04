#!/usr/bin/env python3
"""Exit Plan Mode Hook.

Prompts user before exiting plan mode when a plan exists. This hook intercepts
the ExitPlanMode tool via PreToolUse lifecycle to ask whether to save to GitHub
or implement immediately.

Exit codes:
    0: Success (allow exit - no plan, skip marker present, or no session)
    2: Block (plan exists, no skip marker - prompt user)

This command is invoked via:
    dot-agent kit-command erk exit-plan-mode-hook
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import click

from dot_agent_kit.data.kits.erk.session_plan_extractor import extract_slugs_from_session


def _get_session_id_from_stdin() -> str | None:
    """Read session ID from stdin if available."""
    if sys.stdin.isatty():
        return None
    try:
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            context = json.loads(stdin_data)
            return context.get("session_id")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _get_scratch_dir(session_id: str) -> Path | None:
    """Get scratch directory path in .erk/scratch/<session_id>/.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to scratch directory, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root / ".erk" / "scratch" / session_id
    except subprocess.CalledProcessError:
        return None


def _get_skip_marker_path(session_id: str) -> Path | None:
    """Get skip marker path in .erk/scratch/<session_id>/.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to skip marker file, or None if not in a git repo
    """
    scratch_dir = _get_scratch_dir(session_id)
    if scratch_dir is None:
        return None
    return scratch_dir / "skip-plan-save"


def _get_saved_marker_path(session_id: str) -> Path | None:
    """Get saved marker path in .erk/scratch/<session_id>/.

    The saved marker indicates the plan was already saved to GitHub,
    so exit should proceed without triggering implementation.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to saved marker file, or None if not in a git repo
    """
    scratch_dir = _get_scratch_dir(session_id)
    if scratch_dir is None:
        return None
    return scratch_dir / "plan-saved-to-github"


def _find_session_plan(session_id: str) -> Path | None:
    """Find plan file for the given session using slug lookup.

    Args:
        session_id: The session ID to search for

    Returns:
        Path to plan file if found, None otherwise
    """
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return None

    cwd = os.getcwd()
    slugs = extract_slugs_from_session(session_id, cwd_hint=cwd)
    if not slugs:
        return None

    # Use most recent slug (last in list)
    slug = slugs[-1]
    plan_file = plans_dir / f"{slug}.md"

    if plan_file.exists() and plan_file.is_file():
        return plan_file

    return None


def _output_blocking_message(session_id: str) -> None:
    """Output the blocking message with AskUserQuestion instructions.

    Args:
        session_id: The session ID for the skip marker path
    """
    click.echo("PLAN SAVE PROMPT", err=True)
    click.echo("", err=True)
    click.echo("A plan exists for this session but has not been saved to GitHub.", err=True)
    click.echo("", err=True)
    click.echo("Use AskUserQuestion to ask the user:", err=True)
    click.echo('  "Would you like to save this plan to GitHub first, or implement now?"', err=True)
    click.echo("", err=True)
    click.echo("Options:", err=True)
    click.echo(
        '  - "Save to GitHub" (default): Save plan to GitHub and stop. '
        "Does NOT proceed to implementation.",
        err=True,
    )
    click.echo(
        '  - "Implement now": Skip saving, proceed directly to implementation.',
        err=True,
    )
    click.echo("", err=True)
    click.echo("If user chooses 'Save to GitHub':", err=True)
    click.echo("  1. Run /erk:save-plan", err=True)
    click.echo("  2. Create saved marker:", err=True)
    click.echo(
        f"     mkdir -p .erk/scratch/{session_id} && "
        f"touch .erk/scratch/{session_id}/plan-saved-to-github",
        err=True,
    )
    click.echo("  3. Call ExitPlanMode", err=True)
    click.echo("", err=True)
    click.echo("If user chooses 'Implement now':", err=True)
    click.echo("  1. Create skip marker:", err=True)
    click.echo(
        f"     mkdir -p .erk/scratch/{session_id} && "
        f"touch .erk/scratch/{session_id}/skip-plan-save",
        err=True,
    )
    click.echo("  2. Call ExitPlanMode", err=True)


@click.command(name="exit-plan-mode-hook")
def exit_plan_mode_hook() -> None:
    """Prompt user about plan saving when ExitPlanMode is called.

    This PreToolUse hook intercepts ExitPlanMode calls to ask the user
    whether to save the plan to GitHub or implement immediately.

    Exit codes:
        0: Success - allow exit (no plan, skip marker, or no session)
        2: Block - plan exists, prompt user for action
    """
    session_id = _get_session_id_from_stdin()

    if not session_id:
        click.echo("No session context available, allowing exit")
        sys.exit(0)

    # Check for skip marker first (user chose "Implement now")
    skip_marker = _get_skip_marker_path(session_id)
    if skip_marker and skip_marker.exists():
        skip_marker.unlink()  # Delete marker (one-time use)
        click.echo("Skip marker found, allowing exit")
        sys.exit(0)

    # Check for saved marker (user chose "Save to GitHub" - terminal action)
    saved_marker = _get_saved_marker_path(session_id)
    if saved_marker and saved_marker.exists():
        saved_marker.unlink()  # Delete marker (one-time use)
        click.echo("Plan already saved to GitHub, exiting without implementation")
        click.echo("", err=True)
        click.echo("PLAN_SAVED_NO_IMPLEMENT", err=True)
        sys.exit(0)

    # Check if plan exists for this session
    plan_file = _find_session_plan(session_id)
    if not plan_file:
        click.echo("No plan file found for this session, allowing exit")
        sys.exit(0)

    # Plan exists, no skip marker - BLOCK and instruct
    _output_blocking_message(session_id)
    sys.exit(2)


if __name__ == "__main__":
    exit_plan_mode_hook()
