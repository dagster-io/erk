"""Plan command group."""

import click

from erk.cli.commands.plan.check_cmd import check_plan
from erk.cli.commands.plan.close_cmd import close_plan
from erk.cli.commands.plan.create_cmd import create_plan
from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import list_plans
from erk.cli.commands.plan.log_cmd import plan_log
from erk.core.codespace import Codespace, RealCodespace


@click.group("plan", invoke_without_command=True)
@click.option("--local", is_flag=True, help="Plan in current directory instead of remote Codespace")
@click.option("--desc", "-d", "description", default="", help="Planning session description")
@click.pass_context
def plan_group(ctx: click.Context, local: bool, description: str) -> None:
    """Manage implementation plans.

    When called without a subcommand, launches planning mode:

    \b
      erk plan                     # Remote: Codespace + auto-execute Claude
      erk plan -d "add user auth"  # Remote with description
      erk plan --local             # Local: run Claude in current directory

    Subcommands for plan management:

    \b
      erk plan list                # List all plans
      erk plan get 42              # Get specific plan
      erk plan create              # Create plan from file
      erk plan check               # Validate plan format
      erk plan close 42            # Close a plan
      erk plan log 42              # Show plan event log
    """
    if ctx.invoked_subcommand is None:
        # Get codespace from context for testability, default to RealCodespace
        codespace: Codespace = ctx.obj if isinstance(ctx.obj, Codespace) else RealCodespace()
        if local:
            codespace.run_local_planning(description)
        else:
            codespace.run_remote_planning(description)


plan_group.add_command(check_plan)
plan_group.add_command(close_plan)
plan_group.add_command(create_plan, name="create")
plan_group.add_command(get_plan)
plan_group.add_command(list_plans)
plan_group.add_command(plan_log, name="log")
