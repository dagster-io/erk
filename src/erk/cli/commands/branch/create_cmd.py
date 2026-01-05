"""Branch create command - create a new branch with optional slot assignment."""

import sys
from datetime import UTC, datetime

import click

from erk.cli.commands.slot.common import (
    find_branch_assignment,
    find_inactive_slot,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
    handle_pool_full_interactive,
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
@click.option("--no-slot", is_flag=True, help="Create branch without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@click.pass_obj
def branch_create(ctx: ErkContext, branch_name: str, no_slot: bool, force: bool) -> None:
    """Create a NEW branch and optionally assign it to a pool slot.

    BRANCH is the name of the new git branch to create.

    By default, the command will:
    1. Verify the branch does NOT already exist (fails if it does)
    2. Create the branch from trunk
    3. Find the next available slot in the pool
    4. Create a worktree for that slot
    5. Assign the branch to the slot

    Use --no-slot to create a branch without assigning it to a slot.
    Use `erk br assign` to assign an EXISTING branch to a slot.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Check if branch already exists
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name in local_branches:
        user_output(
            f"Error: Branch '{branch_name}' already exists.\n"
            "Use `erk br assign` to assign an existing branch to a slot."
        )
        raise SystemExit(1) from None

    # Create the new branch from trunk
    trunk = ctx.git.detect_trunk_branch(repo.root)
    ctx.git.create_branch(repo.root, branch_name, trunk)
    ctx.graphite.track_branch(repo.root, branch_name, trunk)
    user_output(f"Created branch: {branch_name}")

    # If --no-slot is specified, we're done
    if no_slot:
        return

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

    # Check if branch is already assigned (shouldn't happen since we just created it)
    existing = find_branch_assignment(state, branch_name)
    if existing is not None:
        user_output(f"Error: Branch '{branch_name}' already assigned to {existing.slot_name}")
        raise SystemExit(1) from None

    # First, prefer pre-initialized slots (fast path)
    inactive_slot = find_inactive_slot(state)
    if inactive_slot is not None:
        slot_name = inactive_slot.name
        worktree_path = repo.worktrees_dir / slot_name

        # Checkout the branch in the existing worktree
        ctx.git.checkout_branch(worktree_path, branch_name)
    else:
        # Fall back to on-demand slot creation
        slot_num = find_next_available_slot(state, repo.worktrees_dir)
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

            # Use the slot we just unassigned (it has a worktree directory that can be reused)
            slot_name = to_unassign.slot_name
            worktree_path = to_unassign.worktree_path
        else:
            slot_name = generate_slot_name(slot_num)
            worktree_path = repo.worktrees_dir / slot_name

        # Create directory for worktree if needed
        worktree_path.mkdir(parents=True, exist_ok=True)

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
        slots=state.slots,
        assignments=(*state.assignments, new_assignment),
    )

    # Save state
    save_pool_state(repo.pool_json_path, new_state)

    user_output(click.style(f"✓ Assigned {branch_name} to {slot_name}", fg="green"))
