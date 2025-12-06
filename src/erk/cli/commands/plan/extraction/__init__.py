"""Extraction subcommand group for plan documentation extraction workflow."""

import click

from erk.cli.commands.plan.extraction.complete_cmd import complete_extraction
from erk.cli.commands.plan.extraction.create_raw_cmd import create_raw


@click.group("extraction")
def extraction_group() -> None:
    """Manage documentation extraction plans."""
    pass


extraction_group.add_command(complete_extraction, name="complete")
extraction_group.add_command(create_raw, name="raw")
