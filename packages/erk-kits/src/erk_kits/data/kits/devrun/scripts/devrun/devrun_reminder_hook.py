#!/usr/bin/env python3
"""
Devrun Reminder Command

Outputs the devrun agent reminder for UserPromptSubmit hook.
This command is invoked via erk kit exec devrun devrun-reminder-hook.
"""

import click

from erk.kits.hooks.decorators import logged_hook, project_scoped


@click.command()
@logged_hook
@project_scoped
def devrun_reminder_hook() -> None:
    """Output devrun agent reminder for UserPromptSubmit hook."""
    click.echo(
        "🚫 No direct Bash for: pytest/pyright/ruff/prettier/make/gt; "
        "✅ Use Task(subagent_type='devrun') instead."
    )


if __name__ == "__main__":
    devrun_reminder_hook()
