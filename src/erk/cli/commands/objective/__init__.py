"""Objective management commands."""

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.objective.check_cmd import check_objective
from erk.cli.commands.objective.close_cmd import close_objective
from erk.cli.commands.objective.inspect_cmd import inspect_objective
from erk.cli.commands.objective.list_cmd import list_objectives
from erk.cli.commands.objective.plan_cmd import plan_objective
from erk.cli.commands.objective.view_cmd import view_objective
from erk.cli.help_formatter import ErkCommandGroup


@click.group("objective", cls=ErkCommandGroup, grouped=False)
def objective_group() -> None:
    """Manage objectives (multi-PR coordination issues)."""
    pass


register_with_aliases(objective_group, check_objective)
register_with_aliases(objective_group, close_objective)
register_with_aliases(objective_group, plan_objective)
register_with_aliases(objective_group, inspect_objective)
register_with_aliases(objective_group, list_objectives)
register_with_aliases(objective_group, view_objective)
