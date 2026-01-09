"""Branch create command - create a new branch with optional slot assignment."""

import click

from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
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

    # Allocate a slot for the branch (branch already exists, so this just assigns)
    result = allocate_slot_for_branch(
        ctx,
        repo,
        branch_name,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )
    user_output(click.style(f"✓ Assigned {branch_name} to {result.slot_name}", fg="green"))
