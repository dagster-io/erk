"""Create-from command - create a worktree slot for an existing branch."""

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
)
from erk.cli.commands.checkout_helpers import display_sync_status, navigate_to_worktree
from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("create-from", cls=CommandWithHiddenOptions)
@click.argument("branch")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def create_from_wt(ctx: ErkContext, branch: str, force: bool, script: bool) -> None:
    """Create a worktree slot for an existing BRANCH.

    Allocates a fresh pool slot for an existing branch and navigates to it.
    Use this when you need a separate worktree for work that already has a branch.

    Examples:

    \b
      erk wt create-from feature-auth
      erk wt create-from feature-auth --force
      source <(erk wt create-from feature-auth --script)
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Validate branch is not trunk
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo.root)
    if branch == trunk_branch:
        user_output(
            f'Error: Cannot create worktree for trunk branch "{trunk_branch}".\n'
            f"The trunk branch should be checked out in the root worktree.\n"
            f"To switch to {trunk_branch}, use:\n"
            f"  erk wt co root"
        )
        raise SystemExit(1) from None

    # Ensure branch exists locally
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    if branch not in local_branches:
        remote_branches = ctx.git.branch.list_remote_branches(repo.root)
        remote_ref = f"origin/{branch}"
        if remote_ref in remote_branches:
            user_output(f"Branch '{branch}' exists on origin, creating local tracking branch...")
            ctx.git.remote.fetch_branch(repo.root, "origin", branch)
            ctx.branch_manager.create_tracking_branch(repo.root, branch, remote_ref)
        else:
            user_output(
                f"Error: Branch '{branch}' does not exist.\n"
                f"To create a new branch, use:\n"
                f"  erk br create {branch}"
            )
            raise SystemExit(1) from None

    # Allocate slot for the branch
    result = allocate_slot_for_branch(
        ctx,
        repo,
        branch,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )

    # Navigate to the worktree
    should_output = navigate_to_worktree(
        ctx,
        worktree_path=result.worktree_path,
        branch=branch,
        script=script,
        command_name="create-from",
        script_message=(
            f'echo "Branch {branch} already in slot {result.slot_name}"'
            if result.already_assigned
            else f'echo "Assigned {branch} to {result.slot_name}"'
        ),
        relative_path=None,
        post_cd_commands=None,
    )

    if not should_output:
        return

    styled_branch = click.style(branch, fg="yellow")
    styled_slot = click.style(result.slot_name, fg="cyan")

    if result.already_assigned:
        user_output(f"Branch {styled_branch} already assigned to {styled_slot}")
    else:
        user_output(click.style("✓ ", fg="green") + f"Assigned {styled_branch} to {styled_slot}")

    display_sync_status(ctx, worktree_path=result.worktree_path, branch=branch, script=script)

    activation_script_path = ensure_worktree_activate_script(
        worktree_path=result.worktree_path,
        post_create_commands=None,
    )
    print_activation_instructions(
        activation_script_path,
        source_branch=None,
        force=False,
        config=activation_config_activate_only(),
        copy=True,
    )
