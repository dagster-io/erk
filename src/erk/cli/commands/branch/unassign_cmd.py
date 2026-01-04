"""Branch unassign command - remove a branch assignment from a pool slot."""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.commands.slot.common import get_placeholder_branch_name
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import user_output


@dataclass(frozen=True)
class UnassignResult:
    """Result of an unassign operation."""

    branch_name: str
    slot_name: str
    trunk_branch: str


def execute_unassign(
    ctx: ErkContext,
    repo: RepoContext,
    state: PoolState,
    assignment: SlotAssignment,
) -> UnassignResult:
    """Execute the unassign operation for a pool slot.

    This function handles:
    - Checking for uncommitted changes
    - Getting or creating placeholder branch
    - Checking out placeholder branch
    - Removing assignment from pool state

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        state: Current pool state
        assignment: The assignment to remove

    Returns:
        UnassignResult with branch name, slot name, and trunk branch

    Raises:
        SystemExit: If worktree has uncommitted changes or placeholder branch cannot be determined
    """
    # Check for uncommitted changes before switching branches
    if ctx.git.has_uncommitted_changes(assignment.worktree_path):
        user_output(
            f"Error: Worktree has uncommitted changes at {assignment.worktree_path}.\n"
            "Commit or stash your changes before unassigning."
        )
        raise SystemExit(1) from None

    # Get or create placeholder branch
    placeholder_branch = get_placeholder_branch_name(assignment.slot_name)
    if placeholder_branch is None:
        user_output(
            f"Error: Could not determine placeholder branch for slot {assignment.slot_name}."
        )
        raise SystemExit(1) from None

    trunk_branch = ctx.git.detect_trunk_branch(repo.root)
    local_branches = ctx.git.list_local_branches(repo.root)

    if placeholder_branch not in local_branches:
        ctx.git.create_branch(repo.root, placeholder_branch, trunk_branch)

    # Checkout placeholder branch in the worktree
    ctx.git.checkout_branch(assignment.worktree_path, placeholder_branch)

    # Remove assignment from state (immutable update)
    new_assignments = tuple(a for a in state.assignments if a.slot_name != assignment.slot_name)
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=state.slots,
        assignments=new_assignments,
    )

    # Save updated state
    save_pool_state(repo.pool_json_path, new_state)

    return UnassignResult(
        branch_name=assignment.branch_name,
        slot_name=assignment.slot_name,
        trunk_branch=trunk_branch,
    )


def _find_assignment_by_slot(state: PoolState, slot_name: str) -> SlotAssignment | None:
    """Find an assignment by slot name.

    Args:
        state: Current pool state
        slot_name: A slot name (e.g., "erk-managed-wt-01")

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.slot_name == slot_name:
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
    if not cwd.exists():
        return None
    resolved_cwd = cwd.resolve()
    for assignment in state.assignments:
        if not assignment.worktree_path.exists():
            continue
        wt_path = assignment.worktree_path.resolve()
        if resolved_cwd == wt_path or wt_path in resolved_cwd.parents:
            return assignment
    return None


@click.command("unassign")
@click.argument("worktree", metavar="WORKTREE", required=False)
@click.pass_obj
def branch_unassign(ctx: ErkContext, worktree: str | None) -> None:
    """Remove a branch assignment from a pool slot.

    WORKTREE is the slot name (e.g., erk-managed-wt-01).

    If no argument is provided, the current pool slot is detected from the
    working directory.

    The worktree directory is kept for reuse with future assignments.

    Examples:
        erk br unassign erk-managed-wt-01    # Unassign by worktree name
        erk br unassign                      # Unassign current slot (from within pool worktree)
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk br create` first.")
        raise SystemExit(1) from None

    # Find the assignment to remove
    assignment: SlotAssignment | None = None

    if worktree is not None:
        # Find by slot name
        assignment = _find_assignment_by_slot(state, worktree)
        if assignment is None:
            user_output(
                f"Error: No worktree found for '{worktree}'.\n"
                "Run `erk slot list` to see current assignments."
            )
            raise SystemExit(1) from None
    else:
        # Detect current slot from cwd
        assignment = _find_assignment_by_cwd(state, ctx.cwd)
        if assignment is None:
            user_output(
                "Error: Not inside a pool slot. Specify worktree name.\n"
                "Usage: erk br unassign WORKTREE"
            )
            raise SystemExit(1) from None

    # Execute the unassign operation
    result = execute_unassign(ctx, repo, state, assignment)

    user_output(
        click.style("✓ ", fg="green")
        + f"Unassigned {click.style(result.branch_name, fg='yellow')} "
        + f"from {click.style(result.slot_name, fg='cyan')}"
    )
    user_output("  Switched to placeholder branch")
    user_output("  Tip: Use 'erk wt co root' to return to root worktree")
