#!/usr/bin/env python3
"""Tripwires Reminder Hook."""

import click

from erk.hooks.decorators import HookContext, hook_command


@hook_command()
def tripwires_reminder_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """Output tripwires reminder for UserPromptSubmit hook."""
    # Scope check: only run in erk-managed projects
    if not hook_ctx.is_erk_project:
        return

    click.echo("🚧 Ensure docs/learned/tripwires.md is loaded and follow its directives.")


if __name__ == "__main__":
    tripwires_reminder_hook()
