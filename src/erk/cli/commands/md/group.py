"""Markdown file command group."""

import click

from erk.cli.commands.md.check import check_command


@click.group(name="md")
def md_group() -> None:
    """Manage and validate markdown context files."""


# Register commands
md_group.add_command(check_command)
