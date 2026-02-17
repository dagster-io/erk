"""Objective commands for remote codespace execution."""

import click

from erk.cli.commands.codespace.run.objective.plan_cmd import run_plan
from erk.cli.help_formatter import ErkCommandGroup


@click.group("objective", cls=ErkCommandGroup, grouped=False)
def objective_group() -> None:
    """Run objective commands remotely on a codespace."""


objective_group.add_command(run_plan)
