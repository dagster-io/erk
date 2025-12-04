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
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                context = json.loads(stdin_data)
                return context.get("session_id")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _get_skip_marker_path(session_id: str) -> Path | None:
    """Get skip marker path in .erk/scratch/<session_id>/.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to skip marker file, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root / ".erk" / "scratch" / session_id / "skip-plan-save"
    except subprocess.CalledProcessError:
        return None


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
    click.echo('  - "Save to GitHub": Run /erk:save-plan, then call ExitPlanMode again', err=True)
    click.echo('  - "Implement now": Create skip marker, then call ExitPlanMode again', err=True)
    click.echo("", err=True)
    click.echo("If user chooses 'Implement now', run this command first:", err=True)
    click.echo(
        f"  mkdir -p .erk/scratch/{session_id} && touch .erk/scratch/{session_id}/skip-plan-save",
        err=True,
    )


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

    # Check for skip marker first
    skip_marker = _get_skip_marker_path(session_id)
    if skip_marker and skip_marker.exists():
        skip_marker.unlink()  # Delete marker (one-time use)
        click.echo("Skip marker found, allowing exit")
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
