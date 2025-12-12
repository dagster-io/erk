#!/usr/bin/env python3
"""Tripwires Reminder Hook."""

import click

from erk.kits.hooks.decorators import project_scoped


@click.command()
@project_scoped
def tripwires_reminder_hook() -> None:
    """Output tripwires reminder for UserPromptSubmit hook."""
    click.echo("🚧 Ensure docs/agent/tripwires.md is loaded and follow its directives.")


if __name__ == "__main__":
    tripwires_reminder_hook()
