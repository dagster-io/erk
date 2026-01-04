"""Pooled plan command - get into a pooled worktree with Claude launched."""

import sys
from datetime import UTC, datetime

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.pooled.common import (
    find_branch_assignment,
    find_inactive_slot,
    find_next_available_slot,
    generate_slot_name,
    get_pool_size,
    handle_pool_full_interactive,
)
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk_shared.output.output import machine_output, user_output


@click.command("plan", cls=CommandWithHiddenOptions)
@click.argument("branch_name", metavar="BRANCH")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def pooled_plan(ctx: ErkContext, branch_name: str, force: bool, script: bool) -> None:
    """Get into a pooled worktree with Claude launched, ready to plan.

    BRANCH is the name of the branch to work on.

    This command combines assignment and activation:
    1. If branch is already in pool, uses existing slot
    2. If branch exists but not in pool, assigns it to a slot
    3. If branch doesn't exist, creates it from trunk and assigns to pool
    4. Activates the worktree with Claude launched

    Examples:
        erk pooled plan my-feature    # Create/assign and activate with Claude
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
            assignments=(),
            slots=(),
        )

    # Check if branch is already assigned to pool
    existing_assignment = find_branch_assignment(state, branch_name)
    if existing_assignment is not None:
        # Branch already in pool - just activate with Claude
        _activate_with_claude(ctx, existing_assignment.worktree_path, script)
        return

    # Check if branch exists
    local_branches = ctx.git.list_local_branches(repo.root)
    branch_exists = branch_name in local_branches

    # First, try to find an inactive (initialized but unassigned) slot
    inactive_slot = find_inactive_slot(state)
    if inactive_slot is not None:
        # Use existing initialized slot - worktree already exists
        slot_name = inactive_slot.name
        worktree_path = repo.worktrees_dir / slot_name

        if not branch_exists:
            # Create the new branch from trunk
            trunk = ctx.git.detect_trunk_branch(repo.root)
            ctx.git.create_branch(repo.root, branch_name, trunk)
            user_output(f"Created branch: {branch_name}")

        # Checkout the feature branch (replaces placeholder)
        ctx.git.checkout_branch(worktree_path, branch_name)
        user_output(f"Using initialized slot: {slot_name}")
    else:
        # Fall back to on-demand slot creation
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
                assignments=new_assignments,
                slots=state.slots,
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

        # Create directory for worktree if needed
        worktree_path.mkdir(parents=True, exist_ok=True)

        if not branch_exists:
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
        slots=state.slots,
    )

    # Save state
    save_pool_state(repo.pool_json_path, new_state)

    user_output(click.style(f"✓ Assigned {branch_name} to {slot_name}", fg="green"))

    # Activate the worktree with Claude
    _activate_with_claude(ctx, worktree_path, script)


def _activate_with_claude(ctx: ErkContext, worktree_path, script: bool) -> None:
    """Activate worktree and launch Claude.

    Args:
        ctx: Erk context
        worktree_path: Path to the worktree to activate
        script: Whether to output script path or user message
    """
    if script:
        activation_script = render_activation_script(
            worktree_path=worktree_path,
            target_subpath=None,
            post_cd_commands=None,
            final_message="claude",
            comment="pooled plan activation",
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name="pooled plan",
            comment="activate and launch claude",
        )
        machine_output(str(result.path), nl=False)
    else:
        user_output(
            "Shell integration not detected. Run 'erk init --shell' to set up automatic activation."
        )
        user_output("\nOr use: source <(erk pooled plan --script)")
    raise SystemExit(0)
