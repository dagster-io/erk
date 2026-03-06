"""Slot assign command - assign an existing branch to a worktree slot."""

import click

from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.output.output import user_output


@click.command("assign")
@click.argument("branch_name", metavar="BRANCH", required=False, default=None)
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@click.option(
    "--from-current-branch",
    is_flag=True,
    help="Move the current branch to a pool slot and switch the current worktree away",
)
@click.pass_obj
def slot_assign(
    ctx: ErkContext, branch_name: str | None, force: bool, from_current_branch: bool
) -> None:
    """Assign an EXISTING branch to an available pool slot.

    BRANCH is the name of an existing git branch to assign to the pool.

    The command will:
    1. Verify the branch EXISTS (fails if it doesn't)
    2. Find the next available slot in the pool
    3. Create a worktree for that slot if needed
    4. Assign the branch to the slot
    5. Persist the assignment to pool.json

    Use --from-current-branch to move the current branch to a slot,
    switching the current worktree to the parent or trunk branch.

    Use `erk branch create` to create a NEW branch and assign it.
    """
    # Validate mutually exclusive arguments
    if from_current_branch and branch_name is not None:
        user_output("Error: Cannot specify both BRANCH and --from-current-branch")
        raise SystemExit(1) from None
    if not from_current_branch and branch_name is None:
        user_output("Error: Must specify either BRANCH or --from-current-branch")
        raise SystemExit(1) from None

    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    if from_current_branch:
        current_branch = Ensure.not_none(
            ctx.git.branch.get_current_branch(ctx.cwd), "Unable to determine current branch"
        )

        # Determine preferred branch to switch to (prioritize Graphite parent)
        parent_branch = ctx.branch_manager.get_parent_branch(repo.root, current_branch)
        to_branch = parent_branch or ctx.git.branch.detect_trunk_branch(repo.root)

        # Validate: can't move trunk to a slot and then switch to trunk
        Ensure.invariant(
            current_branch != to_branch,
            f"Cannot use --from-current-branch when on '{current_branch}'.\n"
            f"The current branch cannot be moved to a slot and then checked out again.\n\n"
            f"Alternatives:\n"
            f"  • Switch to a feature branch first, then use --from-current-branch",
        )

        # Switch current worktree away from the branch
        checkout_path = ctx.git.worktree.is_branch_checked_out(repo.root, to_branch)
        if checkout_path is not None:
            # Target branch is in use elsewhere, fall back to detached HEAD
            ctx.branch_manager.checkout_detached(ctx.cwd, current_branch)
        else:
            # Target branch is available, checkout normally
            ctx.branch_manager.checkout_branch(ctx.cwd, to_branch)

        branch_name = current_branch

    # branch_name is guaranteed non-None at this point
    assert branch_name is not None

    # Check if branch exists - assign command requires EXISTING branch
    local_branches = ctx.git.branch.list_local_branches(repo.root)
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
