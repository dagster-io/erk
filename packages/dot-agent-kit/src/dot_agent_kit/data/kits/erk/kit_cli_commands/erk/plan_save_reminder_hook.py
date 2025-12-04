#!/usr/bin/env python3
"""Plan Save Reminder Hook.

Detects recent plan files in ~/.claude/plans/ and reminds the user
to save them to GitHub. This command is invoked via:
    dot-agent kit-command erk plan-save-reminder-hook
"""

import time
from pathlib import Path

import click


@click.command(name="plan-save-reminder-hook")
def plan_save_reminder_hook() -> None:
    """Detect recent plans and remind user to save to GitHub."""
    plans_dir = Path.home() / ".claude" / "plans"

    # Check if plans directory exists
    if not plans_dir.exists():
        return

    # Find files modified in the last 5 minutes
    current_time = time.time()
    five_minutes_ago = current_time - (5 * 60)

    recent_plans = [
        f
        for f in plans_dir.iterdir()
        if f.is_file() and f.suffix == ".md" and f.stat().st_mtime > five_minutes_ago
    ]

    # If no recent plans found, output nothing
    if not recent_plans:
        return

    # Output reminder for the user
    click.echo("📋 Recent plan detected in ~/.claude/plans/")
    click.echo("")
    click.echo("To save to GitHub: /erk:save-plan")
    click.echo("To implement directly: continue with your next message")


if __name__ == "__main__":
    plan_save_reminder_hook()
