"""Pool assign command - assign a branch to a worktree slot."""

from datetime import UTC, datetime

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import user_output

# Default pool configuration
DEFAULT_POOL_SIZE = 4
SLOT_NAME_PREFIX = "erk-managed-wt"


def _generate_slot_name(slot_number: int) -> str:
    """Generate a slot name from a slot number.

    Args:
        slot_number: 1-based slot number

    Returns:
        Formatted slot name like "erk-managed-wt-01"
    """
    return f"{SLOT_NAME_PREFIX}-{slot_number:02d}"


def _find_next_available_slot(state: PoolState) -> int | None:
    """Find the next available slot number.

    Args:
        state: Current pool state

    Returns:
        1-based slot number if available, None if pool is full
    """
    assigned_slots = {a.slot_name for a in state.assignments}

    for slot_num in range(1, state.pool_size + 1):
        slot_name = _generate_slot_name(slot_num)
        if slot_name not in assigned_slots:
            return slot_num

    return None


def _find_branch_assignment(state: PoolState, branch_name: str) -> SlotAssignment | None:
    """Find if a branch is already assigned to a slot.

    Args:
        state: Current pool state
        branch_name: Branch to search for

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.branch_name == branch_name:
            return assignment
    return None


@click.command("assign")
@click.argument("branch_name", metavar="BRANCH")
@click.pass_obj
def pool_assign(ctx: ErkContext, branch_name: str) -> None:
    """Assign a branch to an available pool slot.

    BRANCH is the name of the git branch to assign to the pool.

    The command will:
    1. Find the next available slot in the pool
    2. Create a worktree for that slot if needed
    3. Assign the branch to the slot
    4. Persist the assignment to pool.json
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Load or create pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=DEFAULT_POOL_SIZE,
            assignments=(),
        )

    # Check if branch is already assigned
    existing = _find_branch_assignment(state, branch_name)
    if existing is not None:
        user_output(f"Error: Branch '{branch_name}' already assigned to {existing.slot_name}")
        raise SystemExit(1) from None

    # Find next available slot
    slot_num = _find_next_available_slot(state)
    if slot_num is None:
        user_output(
            f"Error: Pool is full ({state.pool_size} slots). "
            "Run `erk pool list` to see assignments."
        )
        raise SystemExit(1) from None

    slot_name = _generate_slot_name(slot_num)
    worktree_path = repo.worktrees_dir / slot_name

    # Create worktree if it doesn't exist
    if not ctx.git.path_exists(worktree_path):
        # Create directory for worktree
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create the worktree with the branch
        trunk = ctx.git.detect_trunk_branch(repo.root)

        # Check if branch exists
        local_branches = ctx.git.list_local_branches(repo.root)
        if branch_name not in local_branches:
            # Branch doesn't exist - create it from trunk
            ctx.git.create_branch(repo.root, branch_name, trunk)
            user_output(f"Created branch: {branch_name}")

        # Add worktree
        ctx.git.add_worktree(
            repo.root,
            worktree_path,
            branch=branch_name,
            ref=None,
            create_branch=False,
        )
    else:
        # Worktree exists - check out the branch
        Ensure.invariant(
            ctx.git.is_dir(worktree_path),
            f"Expected {worktree_path} to be a directory",
        )
        ctx.git.checkout_branch(worktree_path, branch_name)

    # Create new assignment
    now = datetime.now(UTC).isoformat()
    new_assignment = SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=now,
        worktree_path=worktree_path,
    )

    # Update state with new assignment
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        assignments=(*state.assignments, new_assignment),
    )

    # Save state
    save_pool_state(repo.pool_json_path, new_state)

    user_output(click.style(f"✓ Assigned {branch_name} to {slot_name}", fg="green"))
