#!/usr/bin/env python3
"""
Devrun Reminder Command

Outputs the devrun agent reminder for UserPromptSubmit hook.
This command is invoked via erk kit exec devrun devrun-reminder-hook.
"""

import click

from erk.kits.hooks.decorators import project_scoped


@click.command()
@project_scoped
def devrun_reminder_hook() -> None:
    """Output devrun agent reminder for UserPromptSubmit hook."""
    click.echo("📋 devrun: pytest/pyright/ruff/prettier/make/gt → Task(subagent_type=devrun)")


if __name__ == "__main__":
    devrun_reminder_hook()
