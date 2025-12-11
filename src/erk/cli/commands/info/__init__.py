"""Info command group for viewing information about erk."""

import click

from erk.cli.commands.info.release_notes_cmd import release_notes_cmd


@click.group("info")
def info_group() -> None:
    """View information about erk."""
    pass


info_group.add_command(release_notes_cmd)
