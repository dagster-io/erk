#!/usr/bin/env python3
"""Fake-Driven Testing Reminder Command."""

import click

from erk.kits.hooks.decorators import project_scoped


@click.command()
@project_scoped
def fake_driven_testing_reminder_hook() -> None:
    """Output fake-driven-testing reminder for UserPromptSubmit hook."""
    click.echo("📌 fake-driven-testing: If not loaded, load now. Always abide by its rules.")


if __name__ == "__main__":
    fake_driven_testing_reminder_hook()
