#!/usr/bin/env python3
"""Plan Save Reminder Hook.

Detects plans associated with the current session and reminds the user
to save them to GitHub. Uses session-scoped lookup via slug field to
handle parallel sessions correctly.

This command is invoked via:
    dot-agent kit-command erk plan-save-reminder-hook
"""

import json
import sys
import time
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


def _find_session_plan(session_id: str) -> Path | None:
    """Find plan file for the given session using slug lookup."""
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return None

    # Use cwd as hint for faster project directory lookup
    import os

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


def _find_recent_plans() -> list[Path]:
    """Fallback: find plans modified in the last 5 minutes."""
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return []

    current_time = time.time()
    five_minutes_ago = current_time - (5 * 60)

    return [
        f
        for f in plans_dir.iterdir()
        if f.is_file() and f.suffix == ".md" and f.stat().st_mtime > five_minutes_ago
    ]


@click.command(name="plan-save-reminder-hook")
def plan_save_reminder_hook() -> None:
    """Detect session-specific plans and remind user to save to GitHub."""
    # Try session-scoped lookup first (handles parallel sessions correctly)
    session_id = _get_session_id_from_stdin()

    if session_id:
        plan_file = _find_session_plan(session_id)
        if plan_file:
            click.echo(f"📋 Plan detected for this session: {plan_file.name}")
            click.echo("")
            click.echo("To save to GitHub: /erk:save-plan")
            click.echo("To implement directly: continue with your next message")
            return

    # Fallback: mtime-based detection (when session ID unavailable)
    recent_plans = _find_recent_plans()
    if recent_plans:
        click.echo("📋 Recent plan detected in ~/.claude/plans/")
        click.echo("")
        click.echo("To save to GitHub: /erk:save-plan")
        click.echo("To implement directly: continue with your next message")


if __name__ == "__main__":
    plan_save_reminder_hook()
