#!/usr/bin/env python3
"""Exit Plan Mode Hook.

Auto-saves plan to GitHub when ExitPlanMode is called. This hook intercepts
the ExitPlanMode tool via PreToolUse lifecycle to ensure plans are saved
before exiting plan mode.

Exit codes:
    0: Success (plan saved or no plan to save)
    2: Failure (plan exists but save failed - blocks ExitPlanMode)

This command is invoked via:
    dot-agent kit-command erk exit-plan-mode-hook
"""

import json
import subprocess
import sys

import click


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


def _save_plan_to_github(session_id: str | None) -> dict:
    """Save plan to GitHub using plan-save-to-issue CLI command.

    Args:
        session_id: Optional session ID for scoped plan lookup

    Returns:
        dict with success status and either issue_url or error message
    """
    cmd = ["dot-agent", "run", "erk", "plan-save-to-issue", "--format", "json"]
    if session_id:
        cmd.extend(["--session-id", session_id])

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        # Try to parse JSON error response
        if e.stdout:
            try:
                return json.loads(e.stdout)
            except json.JSONDecodeError:
                pass
        return {"success": False, "error": e.stderr or "Unknown error"}
    except (json.JSONDecodeError, OSError) as e:
        return {"success": False, "error": str(e)}


@click.command(name="exit-plan-mode-hook")
def exit_plan_mode_hook() -> None:
    """Save plan to GitHub when ExitPlanMode is called.

    This PreToolUse hook intercepts ExitPlanMode calls to auto-save
    the plan to GitHub before allowing plan mode to exit.

    Exit codes:
        0: Success - plan saved or no plan found (allow exit)
        2: Error - plan save failed (block exit until resolved)
    """
    session_id = _get_session_id_from_stdin()

    if not session_id:
        click.echo("No session context available, skipping plan save")
        sys.exit(0)

    # Try to save the plan to GitHub
    result = _save_plan_to_github(session_id)

    if result.get("success"):
        issue_url = result.get("issue_url", "")
        click.echo(f"Plan saved to GitHub: {issue_url}")
        sys.exit(0)

    # Check if error is "no plan found" - that's OK, allow exit
    error = result.get("error", "")
    if "No plan found" in error:
        click.echo("No plan file found for this session, skipping save")
        sys.exit(0)

    # Plan exists but save failed - block ExitPlanMode
    click.echo(f"Failed to save plan: {error}", err=True)
    click.echo("Fix the issue and try again, or use /erk:save-plan manually", err=True)
    sys.exit(2)


if __name__ == "__main__":
    exit_plan_mode_hook()
