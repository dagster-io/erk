"""Plan command group."""

import click

from erk.cli.commands.plan.check_cmd import check_plan
from erk.cli.commands.plan.close_cmd import close_plan
from erk.cli.commands.plan.create_cmd import create_plan
from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import list_plans
from erk.cli.commands.plan.log_cmd import plan_log


@click.group("plan")
def plan_group() -> None:
    """Manage implementation plans."""
    pass


plan_group.add_command(check_plan)
plan_group.add_command(close_plan)
plan_group.add_command(create_plan, name="create")
plan_group.add_command(get_plan)
plan_group.add_command(list_plans, name="list")
plan_group.add_command(plan_log, name="log")
