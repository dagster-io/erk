"""Checkout command - find and switch to a worktree by branch name."""

from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import navigate_to_worktree
from erk.cli.commands.completions import complete_branch_names
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.graphite import find_worktrees_containing_branch
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext, ensure_erk_metadata_dir
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.git.abc import WorktreeInfo
from erk_shared.output.output import user_confirm, user_output


def try_switch_root_worktree(ctx: ErkContext, repo: RepoContext, branch: str) -> Path | None:
    """Try to switch root worktree to branch if it's trunk and root is clean.

    This implements the "takeover" behavior where checking out trunk in a clean root
    worktree switches the root to trunk instead of creating a new dated worktree.

    Args:
        ctx: Erk context with git operations
        repo: Repository context
        branch: Branch name to check

    Returns:
        Root worktree path if successful, None otherwise
    """
    # Check if branch is trunk
    if branch != ctx.trunk_branch:
        return None

    # Find root worktree
    worktrees = ctx.git.list_worktrees(repo.root)
    root_worktree = None
    for wt in worktrees:
        if wt.is_root:
            root_worktree = wt
            break

    if root_worktree is None:
        return None

    # Check if root is clean
    if not ctx.git.is_worktree_clean(root_worktree.path):
        return None

    # Switch root to trunk branch
    ctx.git.checkout_branch(root_worktree.path, branch)

    return root_worktree.path


def _ensure_graphite_tracking(
    ctx: ErkContext, *, repo_root: Path, target_path: Path, branch: str, script: bool
) -> None:
    """Ensure branch is tracked by Graphite (idempotent), with user confirmation.

    If the branch is not already tracked, prompts the user and tracks it with
    trunk as parent if confirmed. This enables branches created without Graphite
    (e.g., via erk-queue) to be managed with Graphite locally.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        target_path: Worktree path where `gt track` should run
        branch: Target branch name
        script: Whether to output only the activation script
    """
    # Skip if Graphite is disabled
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_graphite:
        return

    trunk_branch = ctx.trunk_branch
    # Skip if no trunk branch detected (shouldn't happen in checkout context)
    if trunk_branch is None:
        return

    # Skip trunk branch - it's always implicitly tracked
    if branch == trunk_branch:
        return

    # Check if already tracked (LBYL)
    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if branch in all_branches:
        return  # Already tracked, nothing to do

    # In script mode, skip tracking (no interactive prompts allowed)
    if script:
        return

    # Prompt user for confirmation
    if not user_confirm(
        f"Branch '{branch}' is not tracked by Graphite. Track it with parent '{trunk_branch}'?",
        default=False,
    ):
        return

    # Track the branch with trunk as parent
    ctx.graphite.track_branch(target_path, branch, trunk_branch)
    user_output(f"Tracked '{branch}' with Graphite (parent: {trunk_branch})")


def _format_worktree_info(wt: WorktreeInfo, repo_root: Path) -> str:
    """Format worktree information for display.

    Args:
        wt: WorktreeInfo to format
        repo_root: Path to repository root (used to identify root worktree)

    Returns:
        Formatted string like "root (currently on 'main')" or "wt-name (currently on 'feature')"
    """
    current = wt.branch or "(detached HEAD)"
    if wt.path == repo_root:
        return f"  - root (currently on '{current}')"
    else:
        # Get worktree name from path
        wt_name = wt.path.name
        return f"  - {wt_name} (currently on '{current}')"


def _perform_checkout(
    ctx: ErkContext,
    *,
    repo_root: Path,
    target_worktree: WorktreeInfo,
    branch: str,
    script: bool,
    is_newly_created: bool,
    worktrees: list[WorktreeInfo] | None,
) -> None:
    """Perform the actual checkout and switch to a worktree.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        target_worktree: The worktree to switch to
        branch: Target branch name
        script: Whether to output only the activation script
        is_newly_created: Whether the worktree was just created
        worktrees: Optional list of worktrees (for relative path computation)
    """
    target_path = target_worktree.path
    current_branch_in_worktree = target_worktree.branch
    current_cwd = ctx.cwd

    # Compute relative path to preserve directory position
    relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd) if worktrees else None

    # Check if branch is already checked out in the worktree
    need_checkout = current_branch_in_worktree != branch

    # If we need to checkout, do it before generating the activation script
    if need_checkout:
        ctx.git.checkout_branch(target_path, branch)

    # Ensure branch is tracked with Graphite (idempotent)
    _ensure_graphite_tracking(
        ctx, repo_root=repo_root, target_path=target_path, branch=branch, script=script
    )

    if need_checkout and not script:
        # Show stack context in non-script mode
        stack = ctx.graphite.get_branch_stack(ctx.git, repo_root, branch)
        if stack:
            user_output(f"Stack: {' -> '.join(stack)}")
        user_output(f"Checked out '{branch}' in worktree")

    # Compute four-case message for script and user output
    worktree_name = target_path.name
    is_switching_location = current_cwd != target_path

    # Generate styled script message (used for script mode and as basis for user output)
    styled_wt = click.style(worktree_name, fg="cyan", bold=True)
    styled_branch = click.style(branch, fg="yellow")

    if is_newly_created:
        script_message = f'echo "Switched to new worktree {styled_wt}"'
        user_message = f"Switched to new worktree {styled_wt}"
    elif not is_switching_location:
        script_message = f'echo "Already on branch {styled_branch} in worktree {styled_wt}"'
        user_message = f"Already on branch {styled_branch} in worktree {styled_wt}"
    elif not need_checkout:
        if worktree_name == branch:
            script_message = f'echo "Switched to worktree {styled_wt}"'
            user_message = f"Switched to worktree {styled_wt}"
        else:
            script_message = f'echo "Switched to worktree {styled_wt} (branch {styled_branch})"'
            user_message = f"Switched to worktree {styled_wt} (branch {styled_branch})"
    else:
        script_message = (
            f'echo "Switched to worktree {styled_wt} and checked out branch {styled_branch}"'
        )
        user_message = f"Switched to worktree {styled_wt} and checked out branch {styled_branch}"

    # Use consolidated navigation function
    should_output_message = navigate_to_worktree(
        ctx,
        worktree_path=target_path,
        branch=branch,
        script=script,
        command_name="checkout",
        script_message=script_message,
        relative_path=relative_path,
        post_cd_commands=None,
    )

    if should_output_message:
        user_output(user_message)


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("branch", metavar="BRANCH", shell_complete=complete_branch_names)
@script_option
@click.pass_obj
def branch_checkout(ctx: ErkContext, branch: str, script: bool) -> None:
    """Checkout BRANCH by finding and switching to its worktree.

    This command finds which worktree has the specified branch checked out
    and switches to it. If the branch exists but isn't checked out anywhere,
    a worktree is automatically created. If the branch exists on origin but
    not locally, a tracking branch and worktree are created automatically.

    Examples:

        erk br co feature/user-auth      # Checkout existing worktree

        erk br co unchecked-branch       # Auto-create worktree

        erk br co origin-only-branch     # Create tracking branch + worktree

    If multiple worktrees contain the branch, all options are shown.
    """
    # Use existing repo from context if available (for tests), otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Get all worktrees
    worktrees = ctx.git.list_worktrees(repo.root)

    # Find worktrees containing the target branch
    matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

    # Track whether we're creating a new worktree
    is_newly_created = False

    # Handle three cases: no match, one match, multiple matches
    if len(matching_worktrees) == 0:
        # No worktrees have this branch checked out
        # First, try switching clean root worktree if checking out trunk
        root_path = try_switch_root_worktree(ctx, repo, branch)
        if root_path is not None:
            # Successfully switched root to trunk - refresh and jump to it
            worktrees = ctx.git.list_worktrees(repo.root)
            matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)
        else:
            # Root not available or not trunk - auto-create worktree
            _worktree_path, is_newly_created = ensure_worktree_for_branch(
                ctx, repo, branch, is_plan_derived=False
            )

            # Refresh worktree list to include the newly created worktree
            worktrees = ctx.git.list_worktrees(repo.root)
            matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

        # Fall through to jump to the worktree

    if len(matching_worktrees) == 1:
        # Exactly one worktree contains this branch
        target_worktree = matching_worktrees[0]
        _perform_checkout(
            ctx,
            repo_root=repo.root,
            target_worktree=target_worktree,
            branch=branch,
            script=script,
            is_newly_created=is_newly_created,
            worktrees=worktrees,
        )

    else:
        # Multiple worktrees contain this branch
        # Check if any worktree has the branch directly checked out
        directly_checked_out = [wt for wt in matching_worktrees if wt.branch == branch]

        if len(directly_checked_out) == 1:
            # Exactly one worktree has the branch directly checked out - jump to it
            target_worktree = directly_checked_out[0]
            _perform_checkout(
                ctx,
                repo_root=repo.root,
                target_worktree=target_worktree,
                branch=branch,
                script=script,
                is_newly_created=is_newly_created,
                worktrees=worktrees,
            )
        else:
            # Zero or multiple worktrees have it directly checked out
            # Show error message listing all options
            user_output(f"Branch '{branch}' exists in multiple worktrees:")
            for wt in matching_worktrees:
                user_output(_format_worktree_info(wt, repo.root))

            user_output("\nPlease specify which worktree to use.")
            raise SystemExit(1)
