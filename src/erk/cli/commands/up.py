import click

from erk.cli.commands.navigation_helpers import execute_stack_navigation
from erk.cli.graphite_command import GraphiteCommandWithHiddenOptions
from erk.cli.help_formatter import script_option
from erk.core.context import ErkContext


@click.command("up", cls=GraphiteCommandWithHiddenOptions)
@script_option
@click.option(
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
def up_cmd(ctx: ErkContext, script: bool, delete_current: bool, force: bool) -> None:
    """Move to child branch in worktree stack.

    Navigate to target worktree:
      source <(erk up --script)

    Requires Graphite: 'erk config set use_graphite true'
    """
    execute_stack_navigation(
        ctx=ctx,
        direction="up",
        script=script,
        delete_current=delete_current,
        force=force,
    )
