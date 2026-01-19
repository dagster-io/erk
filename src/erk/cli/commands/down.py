import click

from erk.cli.commands.navigation_helpers import execute_stack_navigation
from erk.cli.graphite_command import GraphiteCommandWithHiddenOptions
from erk.cli.help_formatter import script_option
from erk.core.context import ErkContext


@click.command("down", cls=GraphiteCommandWithHiddenOptions)
@script_option
@click.option(
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
def down_cmd(ctx: ErkContext, script: bool, delete_current: bool, force: bool) -> None:
    """Move to parent branch in worktree stack.

    Prints the activation path for the target worktree.
    To navigate automatically, enable shell integration:

      erk config set shell_integration true
      erk init --shell  # Then restart your shell

    With shell integration enabled:
      erk down

    Without shell integration:
      source <(erk down --script)  # Or use the printed activation path

    Requires Graphite to be enabled: 'erk config set use_graphite true'
    """
    execute_stack_navigation(
        ctx=ctx,
        direction="down",
        script=script,
        delete_current=delete_current,
        force=force,
    )
