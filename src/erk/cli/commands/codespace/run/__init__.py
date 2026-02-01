"""Codespace run commands - execute erk commands remotely."""

import click

from erk.cli.commands.codespace.run.objective import objective_group
from erk.cli.help_formatter import ErkCommandGroup


@click.group("run", cls=ErkCommandGroup, grouped=False)
def run_group() -> None:
    """Run erk commands remotely on a codespace.

    Fire-and-forget execution with auto-start of stopped codespaces.
    """


run_group.add_command(objective_group)
