import os
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

import click

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
    render_activation_script,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.debug import debug_log
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.output.output import user_output
from erk_shared.scratch.markers import PENDING_LEARN_MARKER, marker_exists


def check_pending_learn_marker(worktree_path: Path, force: bool) -> None:
    """Check for pending learn marker and block deletion if present.

    This provides friction before worktree deletion to ensure insights are
    extracted from the session logs. The marker is created by `erk pr land`
    and deleted by `erk learn`.

    Args:
        worktree_path: Path to the worktree being deleted
        force: If True, warn but don't block deletion

    Raises:
        SystemExit: If marker exists and force is False
    """
    if not marker_exists(worktree_path, PENDING_LEARN_MARKER):
        return

    if force:
        user_output(
            click.style("Warning: ", fg="yellow") + "Skipping pending learn (--force used).\n"
        )
        return

    user_output(
        click.style("Error: ", fg="red") + "Worktree has pending learn.\n"
        "Run: erk learn\n"
        "Or use --force to skip learn."
    )
    raise SystemExit(1)


def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    Ensure.invariant(
        not ctx.git.status.has_uncommitted_changes(ctx.cwd),
        "Cannot delete current branch with uncommitted changes.\n"
        "Please commit or stash your changes first.",
    )


def verify_pr_closed_or_merged(ctx: ErkContext, repo_root: Path, branch: str, force: bool) -> None:
    """Verify that the branch's PR is closed or merged on GitHub.

    Warns if no PR exists, raises SystemExit if PR is still OPEN (unless force=True).
    Allows deletion for both MERGED and CLOSED PRs (abandoned/rejected work).

    Args:
        ctx: Erk context
        repo_root: Path to the repository root
        branch: Branch name to check
        force: If True, prompt for confirmation instead of blocking on open PRs
    """
    pr_details = ctx.github.get_pr_for_branch(repo_root, branch)

    if isinstance(pr_details, PRNotFound):
        # Warn but continue when no PR exists
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"No pull request found for branch '{branch}'.\n"
            "Proceeding with deletion without PR verification."
        )
        return  # Allow deletion to proceed

    if pr_details.state == "OPEN":
        if force:
            # With --force, skip all prompts and auto-close the PR
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Pull request for branch '{branch}' is still open.\n"
                + f"{pr_details.url}"
            )
            ctx.github.close_pr(repo_root, pr_details.number)
            user_output(f"✓ Closed PR #{pr_details.number}")
            return

        # Block deletion for open PRs (active work in progress)
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is still open.\n"
            + f"{pr_details.url}\n"
            + "Only closed or merged branches can be deleted with --delete-current.\n"
            + "Use -f/--force to delete anyway."
        )
        raise SystemExit(1)


def validate_for_deletion(
    *,
    ctx: ErkContext,
    repo_root: Path,
    current_branch: str,
    worktree_path: Path,
    force: bool,
) -> None:
    """Run all safety checks before deletion.

    This consolidates the validation logic shared by up.py and down.py
    when using --delete-current flag.

    Args:
        ctx: Erk context
        repo_root: Path to the repository root
        current_branch: Name of the branch being deleted
        worktree_path: Path to the worktree being deleted
        force: If True, prompts instead of blocking on open PRs

    Raises:
        SystemExit: If any validation check fails
    """
    check_clean_working_tree(ctx)
    verify_pr_closed_or_merged(ctx, repo_root, current_branch, force)
    check_pending_learn_marker(worktree_path, force)


def delete_branch_and_worktree(
    ctx: ErkContext, repo: RepoContext, branch: str, worktree_path: Path
) -> None:
    """Delete the specified branch and its worktree.

    Uses two-step deletion: git worktree remove, then branch delete.
    Note: remove_worktree already calls prune internally, so no additional prune needed.

    Args:
        ctx: Erk context
        repo: Repository context (uses main_repo_root for safe directory operations)
        branch: Branch name to delete
        worktree_path: Path to the worktree to remove
    """
    # Use main_repo_root (not repo.root) to ensure we escape to a directory that
    # still exists after worktree removal. repo.root equals the worktree path when
    # running from inside a worktree.
    # main_repo_root is always set by RepoContext.__post_init__, but ty doesn't know
    main_repo = repo.main_repo_root if repo.main_repo_root else repo.root

    # Escape the worktree if we're inside it (prevents FileNotFoundError after removal)
    # Both paths must be resolved for reliable comparison - Path.cwd() returns resolved path
    # but worktree_path may not be resolved, causing equality check to fail for same directory
    cwd = Path.cwd().resolve()
    resolved_worktree = worktree_path.resolve()
    if cwd == resolved_worktree or resolved_worktree in cwd.parents:
        os.chdir(main_repo)

    # Remove the worktree (already calls prune internally)
    try:
        ctx.git.worktree.remove_worktree(main_repo, worktree_path, force=True)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from None
    user_output(f"✓ Removed worktree: {click.style(str(worktree_path), fg='green')}")

    # Delete the branch using BranchManager abstraction (respects use_graphite config)
    ctx.branch_manager.delete_branch(main_repo, branch)
    user_output(f"✓ Deleted branch: {click.style(branch, fg='yellow')}")


def find_assignment_by_worktree_path(
    state: PoolState, worktree_path: Path
) -> SlotAssignment | None:
    """Find a slot assignment by its worktree path.

    Args:
        state: Current pool state
        worktree_path: Path to the worktree to find

    Returns:
        SlotAssignment if the worktree is a pool slot, None otherwise
    """
    if not worktree_path.exists():
        return None
    resolved_path = worktree_path.resolve()
    for assignment in state.assignments:
        if not assignment.worktree_path.exists():
            continue
        if assignment.worktree_path.resolve() == resolved_path:
            return assignment
    return None


def activate_target(
    *,
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    preserve_relative_path: bool,
    post_cd_commands: Sequence[str] | None,
    source_branch: str | None,
    force: bool,
    is_root: bool,
) -> NoReturn:
    """Activate a worktree or root repository and exit.

    This is the unified activation function for both worktrees and root repos.
    The is_root parameter determines the messaging.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree/root directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)
        preserve_relative_path: If True, compute and preserve the user's
            relative directory position from the current worktree
        post_cd_commands: Optional shell commands to run after activation (e.g., entry scripts)
        source_branch: Branch being navigated away from. If provided and force is True,
            shows delete hint in activation instructions.
        force: If True and source_branch is provided, shows the delete hint.
        is_root: If True, uses root repo messaging; otherwise uses worktree messaging

    Raises:
        SystemExit: Always raises (either success or error)
    """
    Ensure.path_exists(ctx, target_path, f"Target not found: {target_path}")

    target_name = target_path.name
    same_worktree = target_path.resolve() == ctx.cwd.resolve()

    # Compute relative path to preserve user's position within worktree
    relative_path: Path | None = None
    if preserve_relative_path:
        worktrees = ctx.git.worktree.list_worktrees(repo.root)
        relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)

    # Determine messaging based on whether this is root or a worktree
    if is_root:
        final_message = 'echo "Went to root repo: $(pwd)"'
        script_comment = "work activate-script (root repo)"
        activate_comment = "activate root"
    else:
        final_message = 'echo "Activated worktree: $(pwd)"'
        script_comment = "work activate-script"
        activate_comment = f"activate {target_name}"

    if script:
        activation_script = render_activation_script(
            worktree_path=target_path,
            target_subpath=relative_path,
            post_cd_commands=post_cd_commands,
            final_message=final_message,
            comment=script_comment,
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=activate_comment,
        )

        debug_log(f"{command_name.capitalize()}: Generated script at {result.path}")
        debug_log(f"{command_name.capitalize()}: Script content:\n{activation_script}")
        debug_log(f"{command_name.capitalize()}: File exists? {result.path.exists()}")

        result.output_for_script_handler()
    else:
        script_path = ensure_worktree_activate_script(
            worktree_path=target_path,
            post_create_commands=None,
        )
        print_activation_instructions(
            script_path,
            source_branch=source_branch,
            force=force,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=same_worktree,
        )
    raise SystemExit(0)


def activate_worktree(
    *,
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    command_name: str,
    preserve_relative_path: bool,
    post_cd_commands: Sequence[str] | None,
    source_branch: str | None,
    force: bool,
) -> NoReturn:
    """Activate a worktree and exit.

    This is a convenience wrapper around activate_target() for worktrees.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)
        preserve_relative_path: If True (default), compute and preserve the user's
            relative directory position from the current worktree
        post_cd_commands: Optional shell commands to run after activation (e.g., entry scripts)
        source_branch: Branch being navigated away from. If provided and force is True,
            shows delete hint in activation instructions.
        force: If True and source_branch is provided, shows the delete hint.

    Raises:
        SystemExit: Always raises (either success or error)
    """
    activate_target(
        ctx=ctx,
        repo=repo,
        target_path=target_path,
        script=script,
        command_name=command_name,
        preserve_relative_path=preserve_relative_path,
        post_cd_commands=post_cd_commands,
        source_branch=source_branch,
        force=force,
        is_root=False,
    )


def activate_root_repo(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    command_name: str,
    post_cd_commands: Sequence[str] | None,
    source_branch: str | None,
    force: bool,
) -> NoReturn:
    """Activate the root repository and exit.

    This is a convenience wrapper around activate_target() for root repos.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)
        post_cd_commands: Optional shell commands to run after cd (e.g., git pull)
        source_branch: Branch being navigated away from. If provided and force is True,
            shows delete hint in activation instructions.
        force: If True and source_branch is provided, shows the delete hint.

    Raises:
        SystemExit: Always raises (either success or error)
    """
    # Use main_repo_root (not repo.root) to ensure we reference a directory that
    # still exists after worktree removal. repo.root equals the worktree path when
    # running from inside a worktree.
    root_path = repo.main_repo_root if repo.main_repo_root else repo.root

    activate_target(
        ctx=ctx,
        repo=repo,
        target_path=root_path,
        script=script,
        command_name=command_name,
        preserve_relative_path=True,
        post_cd_commands=post_cd_commands,
        source_branch=source_branch,
        force=force,
        is_root=True,
    )
