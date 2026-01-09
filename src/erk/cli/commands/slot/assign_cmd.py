"""Slot assign command - assign an existing branch to a worktree slot."""

import click

from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.output.output import user_output


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

    Use `erk branch create` to create a NEW branch and assign it.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Check if branch exists - assign command requires EXISTING branch
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name not in local_branches:
        user_output(
            f"Error: Branch '{branch_name}' does not exist.\n"
            "Use `erk branch create` to create a new branch."
        )
        raise SystemExit(1) from None

    # Allocate a slot for the branch
    # Note: allocate_slot_for_branch handles the already-assigned case by returning early
    result = allocate_slot_for_branch(
        ctx,
        repo,
        branch_name,
        force=force,
        reuse_inactive_slots=True,  # Fix: was missing before
        cleanup_artifacts=True,
    )

    # If branch was already assigned, report error (assign command expects unassigned branch)
    if result.already_assigned:
        user_output(f"Error: Branch '{branch_name}' already assigned to {result.slot_name}")
        raise SystemExit(1) from None

    user_output(click.style(f"✓ Assigned {branch_name} to {result.slot_name}", fg="green"))
