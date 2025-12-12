"""Hook commands group."""

import click

from erk.cli.commands.hook import list, show, validate


@click.group(name="hook")
def hook_group() -> None:
    """Manage Claude Code hooks."""


# Register all hook commands
hook_group.add_command(list.list_hooks)
hook_group.add_command(list.ls)
hook_group.add_command(show.show_hook)
hook_group.add_command(validate.validate_hooks)
