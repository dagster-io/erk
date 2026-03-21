"""Slot down command - navigate to parent branch in worktree stack."""

import click

from erk.cli.graphite_command import GraphiteCommandWithHiddenOptions
from erk.cli.help_formatter import script_option
from erk.core.context import ErkContext
from erk_slots.navigation import execute_stack_navigation


@click.command("down", cls=GraphiteCommandWithHiddenOptions)
@click.argument("count", type=int, default=1, required=False)
@script_option
@click.option(
    "-d",
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating down",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force deletion even if marker exists or PR is open (prompts)",
)
@click.pass_obj
def slot_down(ctx: ErkContext, count: int, script: bool, delete_current: bool, force: bool) -> None:
    """Move to parent branch in worktree stack.

    Navigate down COUNT levels (default: 1).

    Navigate to target worktree:
      source <(erk slot down --script)
      source <(erk slot down 2 --script)

    Requires Graphite: 'erk config set use_graphite true'
    """
    execute_stack_navigation(
        ctx=ctx,
        direction="down",
        count=count,
        script=script,
        delete_current=delete_current,
        force=force,
    )
