"""Slot checkout command - checkout a branch into a pool slot."""

from contextlib import nullcontext
from pathlib import Path

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
)
from erk.cli.commands.checkout_helpers import navigate_to_worktree
from erk.cli.core import discover_repo_context
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.cli_alias import alias
from erk_shared.core.script_error import script_error_handler
from erk_shared.output.output import user_output
from erk_slots.common import allocate_slot_for_branch


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("branch", metavar="BRANCH")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Auto-unassign oldest branch if pool is full",
)
@script_option
@click.pass_obj
def slot_checkout(ctx: ErkContext, branch: str, force: bool, script: bool) -> None:
    """Checkout BRANCH into a pool slot.

    If the branch already has a slot, navigates to it. Otherwise,
    allocates a new slot and checks out the branch there.

    The branch must already exist. Use `erk branch create` to create
    a new branch.

    Navigate to target slot:
      source <(erk slot checkout BRANCH --script)

    Examples:

        erk slot checkout feature/auth         # Checkout into a slot
        erk slot checkout feature/auth --force  # Auto-evict if full
    """
    with script_error_handler(ctx) if script else nullcontext():
        _slot_checkout_body(ctx, branch=branch, force=force, script=script)


def _navigate_and_show(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    branch: str,
    script: bool,
    script_message: str,
    user_message: str,
) -> None:
    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch,
        script=script,
        command_name="slot-checkout",
        script_message=script_message,
        relative_path=None,
        post_cd_commands=None,
    )
    if should_output:
        user_output(user_message)
        script_path = ensure_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=None,
        )
        same_worktree = (
            worktree_path.exists()
            and ctx.cwd.exists()
            and worktree_path.resolve() == ctx.cwd.resolve()
        )
        print_activation_instructions(
            script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=same_worktree,
        )


def _slot_checkout_body(ctx: ErkContext, *, branch: str, force: bool, script: bool) -> None:
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

    # Allocate a new slot for the branch (or return existing if already assigned)
    slot_result = allocate_slot_for_branch(
        ctx,
        repo,
        branch,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )

    if slot_result.already_assigned:
        msg = (
            click.style("✓ ", fg="green")
            + f"Branch '{branch}' already assigned to {slot_result.slot_name}"
        )
        _navigate_and_show(
            ctx,
            worktree_path=slot_result.worktree_path,
            branch=branch,
            script=script,
            script_message=f'echo "Branch {branch} already assigned to {slot_result.slot_name}"',
            user_message=msg,
        )
    else:
        msg = (
            click.style("✓ ", fg="green")
            + f"Assigned {click.style(branch, fg='yellow')} "
            + f"to {click.style(slot_result.slot_name, fg='cyan')}"
        )
        _navigate_and_show(
            ctx,
            worktree_path=slot_result.worktree_path,
            branch=branch,
            script=script,
            script_message=f'echo "Assigned {branch} to {slot_result.slot_name}"',
            user_message=msg,
        )
