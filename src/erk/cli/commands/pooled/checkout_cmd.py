"""Pooled checkout command - navigate to a pool slot's worktree by branch name."""

import click

from erk.cli.commands.navigation_helpers import activate_worktree
from erk.cli.commands.pooled.unassign_cmd import _find_assignment_by_cwd
from erk.cli.config import load_config
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk_shared.output.output import user_output


def _find_assignment_by_branch(state: PoolState, branch: str) -> SlotAssignment | None:
    """Find an assignment by branch name.

    Args:
        state: Current pool state
        branch: Branch name to search for

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.branch_name == branch:
            return assignment
    return None


@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("branch", metavar="BRANCH", required=False)
@script_option
@click.pass_obj
def pooled_checkout(ctx: ErkContext, branch: str | None, script: bool) -> None:
    """Switch to a pool slot's worktree by branch name.

    BRANCH is the name of the branch assigned to a pool slot.

    Examples:
        erk pooled checkout feature-branch    # Switch to the slot with this branch
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk pooled create` first.")
        raise SystemExit(1) from None

    # Require branch argument
    if branch is None:
        user_output("Error: Specify branch name to checkout.")
        raise SystemExit(1) from None

    # Find the assignment by branch name
    assignment = _find_assignment_by_branch(state, branch)
    if assignment is None:
        user_output(
            f"Error: No assignment found for branch '{branch}'.\n"
            "Run `erk pooled list` to see current assignments."
        )
        raise SystemExit(1) from None

    # Check if already in this slot
    current_assignment = _find_assignment_by_cwd(state, ctx.cwd)
    if current_assignment is not None and current_assignment.slot_name == assignment.slot_name:
        user_output(f"Error: Already in pool slot '{assignment.slot_name}'.")
        raise SystemExit(1) from None

    # Load config for entry scripts
    config = load_config(repo.root)
    post_cd_commands = config.pool_checkout_commands if config.pool_checkout_commands else None

    # Activate the worktree with entry scripts
    activate_worktree(
        ctx=ctx,
        repo=repo,
        target_path=assignment.worktree_path,
        script=script,
        command_name="pooled checkout",
        preserve_relative_path=True,
        post_cd_commands=post_cd_commands,
    )
