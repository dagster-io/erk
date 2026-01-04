"""Pooled init-slots command - proactively initialize pool slots."""

import click

from erk.cli.commands.pooled.common import (
    generate_slot_name,
    get_placeholder_branch_name,
    get_pool_size,
    is_slot_initialized,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import user_output


@click.command("init-slots")
@click.option(
    "-n",
    "--count",
    type=int,
    help="Number of slots to initialize. Defaults to pool_size from config.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be done without executing destructive operations.",
)
@click.pass_obj
def pooled_init_slots(ctx: ErkContext, count: int | None, *, dry_run: bool) -> None:
    """Initialize pool slots with worktrees and placeholder branches.

    Pre-creates worktrees with placeholder branches so they're ready for
    immediate assignment. This makes `erk pooled plan` and `erk pooled create`
    faster because they can reuse existing worktrees instead of creating new ones.

    By default, initializes slots up to the configured pool_size. Use -n to
    specify a different count.

    Examples:
        erk pooled init-slots       # Initialize all slots up to pool_size
        erk pooled init-slots -n 2  # Initialize just 2 slots
        erk pooled init-slots --dry-run  # Preview without executing
    """
    if dry_run:
        ctx = create_context(dry_run=True)

    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Get effective slot count
    pool_size = get_pool_size(ctx)
    slot_count = count if count is not None else pool_size

    # Validate slot count
    if slot_count < 1:
        user_output("Error: Slot count must be at least 1")
        raise SystemExit(1) from None

    if slot_count > pool_size:
        user_output(
            f"Warning: Requested {slot_count} slots but pool_size is {pool_size}. "
            f"Initializing {pool_size} slots."
        )
        slot_count = pool_size

    # Load or create pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=pool_size,
            slots=(),
            assignments=(),
        )

    # Get trunk branch for placeholder branches
    trunk = ctx.git.detect_trunk_branch(repo.root)
    local_branches = ctx.git.list_local_branches(repo.root)

    initialized_count = 0
    already_initialized_count = 0
    new_slots: list[SlotInfo] = list(state.slots)

    for slot_num in range(1, slot_count + 1):
        slot_name = generate_slot_name(slot_num)
        worktree_path = repo.worktrees_dir / slot_name

        # Check if already initialized
        if is_slot_initialized(state, slot_name):
            already_initialized_count += 1
            continue

        # Get or create placeholder branch
        placeholder_branch = get_placeholder_branch_name(slot_name)
        if placeholder_branch is None:
            user_output(f"Error: Could not generate placeholder branch for {slot_name}")
            continue

        if placeholder_branch not in local_branches:
            ctx.git.create_branch(repo.root, placeholder_branch, trunk)

        # Create worktree directory
        if ctx.dry_run:
            user_output(f"[DRY RUN] Would create directory: {worktree_path}")
        else:
            worktree_path.mkdir(parents=True, exist_ok=True)

        # Create worktree with placeholder branch
        if not ctx.git.path_exists(worktree_path / ".git"):
            ctx.git.add_worktree(
                repo.root,
                worktree_path,
                branch=placeholder_branch,
                ref=None,
                create_branch=False,
            )

        # Add to slots list
        new_slots.append(SlotInfo(name=slot_name))
        initialized_count += 1
        if ctx.dry_run:
            user_output(f"[DRY RUN] Would initialize {slot_name}")
        else:
            user_output(f"  Initialized {slot_name}")

    # Update and save state
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=tuple(new_slots),
        assignments=state.assignments,
    )
    if ctx.dry_run:
        user_output("[DRY RUN] Would save pool state")
    else:
        save_pool_state(repo.pool_json_path, new_state)

    # Report results
    if initialized_count > 0:
        if ctx.dry_run:
            msg = f"[DRY RUN] Would initialize {initialized_count} slots"
        else:
            msg = click.style(f"✓ Initialized {initialized_count} slots", fg="green")
        if already_initialized_count > 0:
            msg += f" ({already_initialized_count} already existed)"
        user_output(msg)
    elif already_initialized_count > 0:
        user_output(f"All {already_initialized_count} slots already initialized")
    else:
        user_output("No slots to initialize")
