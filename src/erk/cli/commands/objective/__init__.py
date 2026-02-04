"""Objective management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.objective.check_cmd import check_objective
from erk.cli.commands.objective.close_cmd import close_objective
from erk.cli.commands.objective.list_cmd import list_objectives
from erk.cli.commands.objective.next_plan_cmd import next_plan
from erk.cli.commands.objective.view_cmd import view_objective
from erk.cli.help_formatter import ErkCommandGroup


@click.group("objective", cls=ErkCommandGroup)
def objective_group() -> None:
    """Manage objectives (multi-PR coordination issues)."""
    pass


register_with_aliases(objective_group, check_objective)
register_with_aliases(objective_group, close_objective)
register_with_aliases(objective_group, list_objectives)
register_with_aliases(objective_group, next_plan)
register_with_aliases(objective_group, view_objective)
