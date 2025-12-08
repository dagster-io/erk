#!/usr/bin/env python3
"""Tripwires Reminder Hook."""

import click


@click.command()
def tripwires_reminder_hook() -> None:
    """Output tripwires reminder for UserPromptSubmit hook."""
    click.echo("🚧 tripwires: After you write code, check for tripwires.")


if __name__ == "__main__":
    tripwires_reminder_hook()
