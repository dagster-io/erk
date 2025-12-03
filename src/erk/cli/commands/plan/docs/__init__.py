"""Docs subcommand group for plan documentation extraction tracking."""

import click

from erk.cli.commands.plan.docs.extract_cmd import extract_docs
from erk.cli.commands.plan.docs.unextract_cmd import unextract_docs
from erk.cli.commands.plan.docs.unextracted_cmd import list_unextracted


@click.group("docs")
def docs_group() -> None:
    """Track documentation extraction from plan sessions."""
    pass


docs_group.add_command(list_unextracted, name="unextracted")
docs_group.add_command(extract_docs, name="extract")
docs_group.add_command(unextract_docs, name="unextract")
