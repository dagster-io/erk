"""Pooled init-slots command - pre-initialize pool worktrees with placeholder branches."""

import click

from erk.cli.commands.pooled.common import (
    generate_placeholder_branch_name,
    generate_slot_name,
    get_pool_size,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
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
    help="Number of slots to initialize (defaults to pool_size from config)",
)
@click.pass_obj
def pooled_init_slots(ctx: ErkContext, count: int | None) -> None:
    """Pre-initialize pool worktrees with placeholder branches.

    Creates worktrees for all slots (or up to COUNT slots) with placeholder
    branches pointing to the trunk. This allows faster slot assignment since
    the worktrees already exist.

    Each slot gets:
    - A placeholder branch named __erk-slot-NN-placeholder__
    - A worktree directory in the pool worktrees location

    Examples:
        erk pooled init-slots       # Initialize all slots (based on pool_size)
        erk pooled init-slots -n 2  # Initialize only 2 slots
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Get slot count from option or config
    pool_size = get_pool_size(ctx)
    slot_count = count if count is not None else pool_size

    if slot_count < 1:
        user_output("Error: Slot count must be at least 1")
        raise SystemExit(1) from None

    # Load or create pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=pool_size,
            assignments=(),
            slots=(),
        )

    # Get trunk branch for placeholder branches
    trunk = ctx.git.detect_trunk_branch(repo.root)

    # Track existing slots for skip detection
    existing_slot_names = {s.name for s in state.slots}
    new_slots: list[SlotInfo] = list(state.slots)
    created_count = 0
    skipped_count = 0

    for slot_num in range(1, slot_count + 1):
        slot_name = generate_slot_name(slot_num)

        # Skip if already in slots list
        if slot_name in existing_slot_names:
            user_output(f"  Skipping {slot_name} (already initialized)")
            skipped_count += 1
            continue

        placeholder_branch = generate_placeholder_branch_name(slot_num)
        worktree_path = repo.worktrees_dir / slot_name

        # Create placeholder branch from trunk if it doesn't exist
        local_branches = ctx.git.list_local_branches(repo.root)
        if placeholder_branch not in local_branches:
            ctx.git.create_branch(repo.root, placeholder_branch, trunk)

        # Create worktree if it doesn't exist
        if not ctx.git.path_exists(worktree_path):
            worktree_path.mkdir(parents=True, exist_ok=True)
            ctx.git.add_worktree(
                repo.root,
                worktree_path,
                branch=placeholder_branch,
                ref=None,
                create_branch=False,
            )
            user_output(click.style("  ✓ ", fg="green") + f"Created {slot_name}")
        else:
            # Worktree exists - ensure it's on the placeholder branch
            current_branch = ctx.git.get_current_branch(worktree_path)
            if current_branch != placeholder_branch:
                ctx.git.checkout_branch(worktree_path, placeholder_branch)
            user_output(click.style("  ✓ ", fg="green") + f"Initialized {slot_name}")

        # Add to slots list
        new_slots.append(SlotInfo(name=slot_name))
        created_count += 1

    # Save updated pool state
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        assignments=state.assignments,
        slots=tuple(new_slots),
    )
    save_pool_state(repo.pool_json_path, new_state)

    # Summary
    user_output("")
    if created_count > 0:
        user_output(click.style(f"✓ Initialized {created_count} slot(s)", fg="green"))
    if skipped_count > 0:
        user_output(f"  Skipped {skipped_count} already-initialized slot(s)")
