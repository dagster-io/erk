"""Slot assign command - assign an existing branch to a worktree slot."""

import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.commands.slot.common import (
    find_branch_assignment,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
    handle_pool_full_interactive,
)
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


def _cleanup_worktree_artifacts(worktree_path: Path) -> None:
    """Remove stale artifacts from a worktree before reuse.

    Cleans up .impl/ and .erk/scratch/ folders which persist across
    branch switches since they are in .gitignore.
    """
    impl_folder = worktree_path / ".impl"
    scratch_folder = worktree_path / ".erk" / "scratch"

    if impl_folder.exists():
        shutil.rmtree(impl_folder)

    if scratch_folder.exists():
        shutil.rmtree(scratch_folder)


@click.command("assign")
@click.argument("branch_name", metavar="BRANCH")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@click.pass_obj
def slot_assign(ctx: ErkContext, branch_name: str, force: bool) -> None:
    """Assign an EXISTING branch to an available pool slot.

    BRANCH is the name of an existing git branch to assign to the pool.

    The command will:
    1. Verify the branch EXISTS (fails if it doesn't)
    2. Find the next available slot in the pool
    3. Create a worktree for that slot if needed
    4. Assign the branch to the slot
    5. Persist the assignment to pool.json

    Use `erk slot create` to create a NEW branch and assign it.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Get pool size from config or default
    pool_size = get_pool_size(ctx)

    # Load or create pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=pool_size,
            slots=(),
            assignments=(),
        )

    # Check if branch is already assigned
    existing = find_branch_assignment(state, branch_name)
    if existing is not None:
        user_output(f"Error: Branch '{branch_name}' already assigned to {existing.slot_name}")
        raise SystemExit(1) from None

    # Check if branch exists - assign command requires EXISTING branch
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name not in local_branches:
        user_output(
            f"Error: Branch '{branch_name}' does not exist.\n"
            "Use `erk slot create` to create a new branch."
        )
        raise SystemExit(1) from None

    # Find next available slot
    slot_num = find_next_available_slot(state)
    if slot_num is None:
        # Pool is full - handle interactively or with --force
        to_unassign = handle_pool_full_interactive(state, force, sys.stdin.isatty())
        if to_unassign is None:
            raise SystemExit(1) from None

        # Remove the assignment from state
        new_assignments = tuple(
            a for a in state.assignments if a.slot_name != to_unassign.slot_name
        )
        state = PoolState(
            version=state.version,
            pool_size=state.pool_size,
            slots=state.slots,
            assignments=new_assignments,
        )
        save_pool_state(repo.pool_json_path, state)
        user_output(
            click.style("✓ ", fg="green")
            + f"Unassigned {click.style(to_unassign.branch_name, fg='yellow')} "
            + f"from {click.style(to_unassign.slot_name, fg='cyan')}"
        )

        # Retry finding a slot - should now succeed
        slot_num = find_next_available_slot(state)
        if slot_num is None:
            # This shouldn't happen, but handle gracefully
            user_output("Error: Failed to find available slot after unassigning")
            raise SystemExit(1) from None

    slot_name = generate_slot_name(slot_num)
    worktree_path = repo.worktrees_dir / slot_name

    # Create worktree if it doesn't exist
    if not ctx.git.path_exists(worktree_path):
        # Create directory for worktree
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Add worktree
        ctx.git.add_worktree(
            repo.root,
            worktree_path,
            branch=branch_name,
            ref=None,
            create_branch=False,
        )
    else:
        # Worktree exists - clean up stale artifacts and check out the branch
        Ensure.invariant(
            ctx.git.is_dir(worktree_path),
            f"Expected {worktree_path} to be a directory",
        )
        _cleanup_worktree_artifacts(worktree_path)
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
        slots=state.slots,
        assignments=(*state.assignments, new_assignment),
    )

    # Save state
    save_pool_state(repo.pool_json_path, new_state)

    user_output(click.style(f"✓ Assigned {branch_name} to {slot_name}", fg="green"))
