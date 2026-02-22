import click

from erk.cli.commands.navigation_helpers import execute_stack_navigation
from erk.cli.graphite_command import GraphiteCommandWithHiddenOptions
from erk.cli.help_formatter import script_option
from erk.core.context import ErkContext


@click.command("up", cls=GraphiteCommandWithHiddenOptions)
@click.argument("count", type=int, default=1, required=False)
@script_option
@click.option(
    "-d",
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating up",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force deletion even if marker exists or PR is open (prompts)",
)
@click.pass_obj
def up_cmd(ctx: ErkContext, count: int, script: bool, delete_current: bool, force: bool) -> None:
    """Move to child branch in worktree stack.

    Navigate up COUNT levels (default: 1).

    Navigate to target worktree:
      source <(erk up --script)
      source <(erk up 3 --script)

    Requires Graphite: 'erk config set use_graphite true'
    """
    execute_stack_navigation(
        ctx=ctx,
        direction="up",
        count=count,
        script=script,
        delete_current=delete_current,
        force=force,
    )
