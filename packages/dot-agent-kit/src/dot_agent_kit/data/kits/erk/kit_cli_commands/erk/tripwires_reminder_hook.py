#!/usr/bin/env python3
"""Tripwires Reminder Hook."""

import click


@click.command()
def tripwires_reminder_hook() -> None:
    """Output tripwires reminder for UserPromptSubmit hook."""
    click.echo(
        "🚧 tripwires: Before os.chdir, /tmp/ writes, dry_run flags, "
        "or subprocess.run → check docs/agent/tripwires.md"
    )


if __name__ == "__main__":
    tripwires_reminder_hook()
