"""Pooled unassign command - remove a branch assignment from a pool slot."""

from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import user_output


def _find_assignment(state: PoolState, slot_or_branch: str) -> SlotAssignment | None:
    """Find an assignment by slot name or branch name.

    Args:
        state: Current pool state
        slot_or_branch: Either a slot name (e.g., "erk-managed-wt-01") or branch name

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.slot_name == slot_or_branch:
            return assignment
        if assignment.branch_name == slot_or_branch:
            return assignment
    return None


def _find_assignment_by_cwd(state: PoolState, cwd: Path) -> SlotAssignment | None:
    """Find an assignment by checking if cwd is within a pool slot's worktree.

    Args:
        state: Current pool state
        cwd: Current working directory

    Returns:
        SlotAssignment if cwd is within a pool slot, None otherwise
    """
    resolved_cwd = cwd.resolve()
    for assignment in state.assignments:
        wt_path = assignment.worktree_path.resolve()
        if resolved_cwd == wt_path or wt_path in resolved_cwd.parents:
            return assignment
    return None


@click.command("unassign")
@click.argument("slot_or_branch", metavar="SLOT_OR_BRANCH", required=False)
@click.pass_obj
def pooled_unassign(ctx: ErkContext, slot_or_branch: str | None) -> None:
    """Remove a branch assignment from a pool slot.

    SLOT_OR_BRANCH can be either a slot name (e.g., erk-managed-wt-01) or a branch name.

    If no argument is provided, the current pool slot is detected from the
    working directory.

    The worktree directory is kept for reuse with future assignments.

    Examples:
        erk pooled unassign erk-managed-wt-01    # Unassign by slot name
        erk pooled unassign feature-branch       # Unassign by branch name
        erk pooled unassign                      # Unassign current slot (from within pool worktree)
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk pooled create` first.")
        raise SystemExit(1) from None

    # Find the assignment to remove
    assignment: SlotAssignment | None = None

    if slot_or_branch is not None:
        # Find by slot name or branch name
        assignment = _find_assignment(state, slot_or_branch)
        if assignment is None:
            user_output(
                f"Error: No assignment found for '{slot_or_branch}'.\n"
                "Run `erk pooled list` to see current assignments."
            )
            raise SystemExit(1) from None
    else:
        # Detect current slot from cwd
        assignment = _find_assignment_by_cwd(state, ctx.cwd)
        if assignment is None:
            user_output(
                "Error: Not inside a pool slot. Specify slot or branch name.\n"
                "Usage: erk pooled unassign SLOT_OR_BRANCH"
            )
            raise SystemExit(1) from None

    # Remove assignment from state (immutable update)
    new_assignments = tuple(a for a in state.assignments if a.slot_name != assignment.slot_name)
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        assignments=new_assignments,
    )

    # Save updated state
    save_pool_state(repo.pool_json_path, new_state)

    user_output(
        click.style("✓ ", fg="green")
        + f"Unassigned {click.style(assignment.branch_name, fg='yellow')} "
        + f"from {click.style(assignment.slot_name, fg='cyan')}"
    )
