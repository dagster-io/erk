"""Pool checkout command - navigate to a pool slot by branch name."""

import click

from erk.cli.alias import alias
from erk.cli.commands.navigation_helpers import activate_worktree
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
)
from erk_shared.output.output import user_output


def _find_branch_assignment(state: PoolState, branch_name: str) -> SlotAssignment | None:
    """Find an assignment by branch name.

    Args:
        state: Current pool state
        branch_name: Branch name to search for

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.branch_name == branch_name:
            return assignment
    return None


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("branch_name", metavar="BRANCH")
@script_option
@click.pass_obj
def pool_checkout(ctx: ErkContext, branch_name: str, script: bool) -> None:
    """Navigate to a pool slot by branch name.

    BRANCH is the name of the git branch assigned to a pool slot.

    With shell integration (recommended):
        erk pool co BRANCH

    The shell wrapper function automatically activates the worktree.
    Run 'erk init --shell' to set up shell integration.

    Without shell integration:
        source <(erk pool co BRANCH --script)

    Example:
        erk pool co feature-work    # Navigate to pool slot with feature-work branch
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output(
            click.style("Error: ", fg="red") + "No pool configured. Run `erk pool assign` first."
        )
        raise SystemExit(1)

    # Find assignment by branch name
    assignment = _find_branch_assignment(state, branch_name)
    if assignment is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Branch '{branch_name}' not found in pool.\n\n"
            + "Hint: Use `erk pool list` to see assigned branches, or\n"
            + f"      `erk pool assign {branch_name}` to assign it to a pool slot."
        )
        raise SystemExit(1)

    # Get worktree path from assignment
    worktree_path = assignment.worktree_path

    # Show worktree and branch info (only in non-script mode)
    if not script:
        styled_slot = click.style(assignment.slot_name, fg="cyan", bold=True)
        styled_branch = click.style(branch_name, fg="yellow")
        user_output(f"Went to pool slot {styled_slot} [{styled_branch}]")

    # Activate the worktree
    activate_worktree(ctx, repo, worktree_path, script, "pool co", preserve_relative_path=True)
