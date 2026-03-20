"""Slot checkout command - checkout a branch into a pool slot."""

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import load_pool_state
from erk_shared.output.output import user_output
from erk_slots.common import (
    allocate_slot_for_branch,
    find_current_slot_assignment,
    update_slot_assignment_tip,
)


@click.command("checkout")
@click.argument("branch", metavar="BRANCH")
@click.option(
    "--new-slot",
    is_flag=True,
    help="Allocate a new slot instead of stacking in place",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Auto-unassign oldest branch if pool is full",
)
@click.pass_obj
def slot_checkout(ctx: ErkContext, branch: str, new_slot: bool, force: bool) -> None:
    """Checkout BRANCH into a pool slot.

    By default, if running inside an assigned slot, updates the slot's
    assignment to the new branch (stack-in-place). Use --new-slot to
    allocate a fresh slot instead.

    The branch must already exist. Use `erk branch create` to create
    a new branch.

    Examples:

        erk slot checkout feature/auth        # Stack in current slot
        erk slot checkout feature/auth --new-slot  # Allocate new slot
        erk slot checkout feature/auth --force     # Auto-evict if full
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Verify branch exists
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    if branch not in local_branches:
        # Check remote
        remote_branches = ctx.git.branch.list_remote_branches(repo.root)
        remote_ref = f"origin/{branch}"
        if remote_ref in remote_branches:
            user_output(f"Branch '{branch}' exists on origin, creating local tracking branch...")
            ctx.git.remote.fetch_branch(repo.root, "origin", branch)
            ctx.branch_manager.create_tracking_branch(repo.root, branch, remote_ref)
        else:
            user_output(
                f"Error: Branch '{branch}' does not exist.\n"
                f"Use `erk branch create` to create a new branch."
            )
            raise SystemExit(1) from None

    # Check for stack-in-place (unless --new-slot)
    if not new_slot:
        state = load_pool_state(repo.pool_json_path)
        if state is not None:
            current_assignment = find_current_slot_assignment(state, repo.root)
            if current_assignment is not None:
                slot_result = update_slot_assignment_tip(
                    repo.pool_json_path,
                    state,
                    current_assignment,
                    branch_name=branch,
                    now=ctx.time.now().isoformat(),
                )
                ctx.branch_manager.checkout_branch(slot_result.worktree_path, branch)
                user_output(
                    click.style(
                        f"✓ Stacked {branch} in {slot_result.slot_name} (in place)",
                        fg="green",
                    )
                )
                return

    # Allocate a new slot for the branch
    slot_result = allocate_slot_for_branch(
        ctx,
        repo,
        branch,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )

    if slot_result.already_assigned:
        user_output(
            click.style("✓ ", fg="green")
            + f"Branch '{branch}' already assigned to {slot_result.slot_name}"
        )
    else:
        user_output(
            click.style("✓ ", fg="green")
            + f"Assigned {click.style(branch, fg='yellow')} "
            + f"to {click.style(slot_result.slot_name, fg='cyan')}"
        )
