"""Pooled create command - create a new branch and assign to a slot."""

from datetime import UTC, datetime

import click

from erk.cli.commands.pooled.common import (
    DEFAULT_POOL_SIZE,
    find_branch_assignment,
    find_next_available_slot,
    generate_slot_name,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import user_output


@click.command("create")
@click.argument("branch_name", metavar="BRANCH")
@click.pass_obj
def pooled_create(ctx: ErkContext, branch_name: str) -> None:
    """Create a NEW branch and assign it to an available pool slot.

    BRANCH is the name of the new git branch to create and assign.

    The command will:
    1. Verify the branch does NOT already exist (fails if it does)
    2. Find the next available slot in the pool
    3. Create the branch from trunk
    4. Create a worktree for that slot
    5. Assign the branch to the slot
    6. Persist the assignment to pool.json

    Use `erk pooled assign` to assign an EXISTING branch to a slot.
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
    existing = find_branch_assignment(state, branch_name)
    if existing is not None:
        user_output(f"Error: Branch '{branch_name}' already assigned to {existing.slot_name}")
        raise SystemExit(1) from None

    # Check if branch already exists - create command requires NEW branch
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name in local_branches:
        user_output(
            f"Error: Branch '{branch_name}' already exists.\n"
            "Use `erk pooled assign` for existing branches."
        )
        raise SystemExit(1) from None

    # Find next available slot
    slot_num = find_next_available_slot(state)
    if slot_num is None:
        user_output(
            f"Error: Pool is full ({state.pool_size} slots). "
            "Run `erk pooled list` to see assignments."
        )
        raise SystemExit(1) from None

    slot_name = generate_slot_name(slot_num)
    worktree_path = repo.worktrees_dir / slot_name

    # Create directory for worktree if needed
    worktree_path.mkdir(parents=True, exist_ok=True)

    # Create the new branch from trunk
    trunk = ctx.git.detect_trunk_branch(repo.root)
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
