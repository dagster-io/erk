"""Pooled switch command - navigate to a pool slot's worktree."""

import click

from erk.cli.commands.navigation_helpers import activate_worktree
from erk.cli.commands.pooled.unassign_cmd import _find_assignment, _find_assignment_by_cwd
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.output.output import user_output


@click.command("switch", cls=CommandWithHiddenOptions)
@click.argument("slot_or_branch", metavar="SLOT_OR_BRANCH", required=False)
@script_option
@click.pass_obj
def pooled_switch(ctx: ErkContext, slot_or_branch: str | None, script: bool) -> None:
    """Switch to a pool slot's worktree.

    SLOT_OR_BRANCH can be either a slot name (e.g., erk-managed-wt-01) or a branch name.

    Examples:
        erk pooled switch erk-managed-wt-01    # Switch by slot name
        erk pooled switch feature-branch       # Switch by branch name
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk pooled create` first.")
        raise SystemExit(1) from None

    # Require slot or branch argument
    if slot_or_branch is None:
        user_output("Error: Specify slot or branch name to switch to.")
        raise SystemExit(1) from None

    # Find the assignment
    assignment = _find_assignment(state, slot_or_branch)
    if assignment is None:
        user_output(
            f"Error: No assignment found for '{slot_or_branch}'.\n"
            "Run `erk pooled list` to see current assignments."
        )
        raise SystemExit(1) from None

    # Check if already in this slot
    current_assignment = _find_assignment_by_cwd(state, ctx.cwd)
    if current_assignment is not None and current_assignment.slot_name == assignment.slot_name:
        user_output(f"Error: Already in pool slot '{assignment.slot_name}'.")
        raise SystemExit(1) from None

    # Activate the worktree
    activate_worktree(ctx, repo, assignment.worktree_path, script, "pooled switch")
