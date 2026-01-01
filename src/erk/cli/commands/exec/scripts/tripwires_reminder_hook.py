#!/usr/bin/env python3
"""Tripwires Reminder Hook."""

import click

from erk.hooks.decorators import logged_hook
from erk_shared.context.helpers import require_repo_root


@click.command()
@click.pass_context
@logged_hook
def tripwires_reminder_hook(ctx: click.Context) -> None:
    """Output tripwires reminder for UserPromptSubmit hook."""
    # Inject repo_root from context
    repo_root = require_repo_root(ctx)

    # Inline scope check: only run in erk-managed projects
    if not (repo_root / ".erk").is_dir():
        return

    click.echo("🚧 Ensure docs/learned/tripwires.md is loaded and follow its directives.")


if __name__ == "__main__":
    tripwires_reminder_hook()
