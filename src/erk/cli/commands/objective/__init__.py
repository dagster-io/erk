"""Objective command group for managing long-running goals."""

import click

from erk.cli.commands.objective.get_cmd import get_objective
from erk.cli.commands.objective.list_cmd import list_objectives
from erk.cli.commands.objective.turn_cmd import turn_objective


@click.group("objective")
def objective_group() -> None:
    """Manage objectives."""
    pass


objective_group.add_command(list_objectives, name="list")
objective_group.add_command(get_objective, name="get")
objective_group.add_command(turn_objective, name="turn")
