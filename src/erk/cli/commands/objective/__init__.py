"""Objective management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.objective.list_cmd import list_objectives
from erk.cli.help_formatter import ErkCommandGroup


@click.group("objective", cls=ErkCommandGroup, hidden=True)
def objective_group() -> None:
    """Manage objectives (multi-PR coordination issues)."""
    pass


register_with_aliases(objective_group, list_objectives)
