"""Machine-readable JSON objective commands (erk json objective ...)."""

import click

from erk.cli.commands.objective.check.json_cli import json_objective_check
from erk.cli.commands.objective.view.json_cli import json_objective_view


@click.group("objective")
def json_objective_group() -> None:
    """Machine-readable objective commands."""
    pass


json_objective_group.add_command(json_objective_view, name="view")
json_objective_group.add_command(json_objective_check, name="check")
