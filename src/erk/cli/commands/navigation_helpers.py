import os
from collections.abc import Sequence
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.debug import debug_log
from erk_shared.git.abc import WorktreeInfo
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import machine_output, user_output
from erk_shared.scratch.markers import PENDING_LEARN_MARKER, marker_exists


def check_pending_learn_marker(worktree_path: Path, force: bool) -> None:
    """Check for pending learn marker and block deletion if present.

    This provides friction before worktree deletion to ensure insights are
    extracted from the session logs. The marker is created by `erk land`
    and deleted by `erk plan learn raw`.

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
        "Run: erk plan learn raw\n"
        "Or use --force to skip learn."
    )
    raise SystemExit(1)


def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    Ensure.invariant(
        not ctx.git.has_uncommitted_changes(ctx.cwd),
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
            # Show warning and prompt for confirmation
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Pull request for branch '{branch}' is still open.\n"
                + f"{pr_details.url}"
            )
            if not ctx.console.confirm("Delete branch anyway?", default=False):
                raise SystemExit(1)
            # Ask if user wants to close the PR
            if ctx.console.confirm("Close the PR?", default=True):
                ctx.github.close_pr(repo_root, pr_details.number)
                user_output(f"✓ Closed PR #{pr_details.number}")
            return  # User confirmed, allow deletion

        # Block deletion for open PRs (active work in progress)
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is still open.\n"
            + f"{pr_details.url}\n"
            + "Only closed or merged branches can be deleted with --delete-current.\n"
            + "Use -f/--force to delete anyway."
        )
        raise SystemExit(1)


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
    ctx.git.remove_worktree(main_repo, worktree_path, force=True)
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


def unallocate_worktree_and_branch(
    ctx: ErkContext,
    repo: RepoContext,
    branch: str,
    worktree_path: Path,
) -> None:
    """Unallocate a worktree and delete its branch.

    If worktree is a pool slot: unassigns slot (keeps directory for reuse), deletes branch.
    If not a pool slot: removes worktree directory, deletes branch.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        branch: Branch name to delete
        worktree_path: Path to the worktree to unallocate
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Check if this is a slot worktree
    state = load_pool_state(repo.pool_json_path)
    assignment: SlotAssignment | None = None
    if state is not None:
        assignment = find_assignment_by_worktree_path(state, worktree_path)

    if assignment is not None:
        # Slot worktree: unassign instead of delete
        # state is guaranteed to be non-None since assignment was found in it
        assert state is not None
        execute_unassign(ctx, repo, state, assignment)
        ctx.branch_manager.delete_branch(main_repo_root, branch)
        user_output(click.style("✓", fg="green") + " Unassigned slot and deleted branch")
    else:
        # Non-slot worktree: delete both
        ctx.git.remove_worktree(main_repo_root, worktree_path, force=True)
        ctx.branch_manager.delete_branch(main_repo_root, branch)
        user_output(click.style("✓", fg="green") + " Removed worktree and deleted branch")


def activate_root_repo(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    command_name: str,
    post_cd_commands: Sequence[str] | None,
) -> None:
    """Activate the root repository and exit.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)
        post_cd_commands: Optional shell commands to run after cd (e.g., git pull)

    Raises:
        SystemExit: Always (successful exit after activation)
    """
    # Use main_repo_root (not repo.root) to ensure we reference a directory that
    # still exists after worktree removal. repo.root equals the worktree path when
    # running from inside a worktree.
    root_path = repo.main_repo_root if repo.main_repo_root else repo.root

    # Compute relative path to preserve user's position within worktree
    worktrees = ctx.git.list_worktrees(repo.root)
    relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)

    if script:
        script_content = render_activation_script(
            worktree_path=root_path,
            target_subpath=relative_path,
            post_cd_commands=post_cd_commands,
            final_message='echo "Went to root repo: $(pwd)"',
            comment="work activate-script (root repo)",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name=command_name,
            comment="activate root",
        )
        machine_output(str(result.path), nl=False)
    else:
        user_output(f"Went to root repo: {root_path}")
        user_output(
            "\nShell integration not detected. "
            "Run 'erk init --shell' to set up automatic activation."
        )
        user_output(f"Or use: source <(erk {command_name} --script)")
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
) -> None:
    """Activate a worktree and exit.

    Args:
        ctx: Erk context (for script_writer)
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)
        preserve_relative_path: If True (default), compute and preserve the user's
            relative directory position from the current worktree
        post_cd_commands: Optional shell commands to run after activation (e.g., entry scripts)

    Raises:
        SystemExit: If worktree not found, or after successful activation
    """
    wt_path = target_path

    Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")

    worktree_name = wt_path.name

    # Auto-compute relative path if requested
    relative_path: Path | None = None
    if preserve_relative_path:
        worktrees = ctx.git.list_worktrees(repo.root)
        relative_path = compute_relative_path_in_worktree(worktrees, ctx.cwd)

    if script:
        activation_script = render_activation_script(
            worktree_path=wt_path,
            target_subpath=relative_path,
            post_cd_commands=post_cd_commands,
            final_message='echo "Activated worktree: $(pwd)"',
            comment="work activate-script",
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=f"activate {worktree_name}",
        )

        debug_log(f"{command_name.capitalize()}: Generated script at {result.path}")
        debug_log(f"{command_name.capitalize()}: Script content:\n{activation_script}")
        debug_log(f"{command_name.capitalize()}: File exists? {result.path.exists()}")

        result.output_for_shell_integration()
    else:
        user_output(
            "Shell integration not detected. Run 'erk init --shell' to set up automatic activation."
        )
        user_output(f"\nOr use: source <(erk {command_name} --script)")
    raise SystemExit(0)


def resolve_up_navigation(
    ctx: ErkContext, repo: RepoContext, current_branch: str, worktrees: list[WorktreeInfo]
) -> tuple[str, bool]:
    """Resolve --up navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at top of stack)
    """
    # Navigate up to child branch
    children = Ensure.truthy(
        ctx.branch_manager.get_child_branches(repo.root, current_branch),
        "Already at the top of the stack (no child branches)",
    )

    # Fail explicitly if multiple children exist
    if len(children) > 1:
        children_list = ", ".join(f"'{child}'" for child in children)
        user_output(
            f"Error: Branch '{current_branch}' has multiple children: {children_list}.\n"
            f"Please create worktree for specific child: erk create <branch-name>"
        )
        raise SystemExit(1)

    # Use the single child
    target_branch = children[0]

    # Check if target branch has a worktree, create if necessary
    target_wt_path = ctx.git.find_worktree_for_branch(repo.root, target_branch)
    if target_wt_path is None:
        # Auto-create worktree for target branch
        _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, target_branch)
        return target_branch, was_created

    return target_branch, False


def resolve_down_navigation(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    current_branch: str,
    worktrees: list[WorktreeInfo],
    trunk_branch: str | None,
) -> tuple[str, bool]:
    """Resolve --down navigation to determine target branch name.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()
        trunk_branch: Configured trunk branch name, or None for auto-detection

    Returns:
        Tuple of (target_branch, was_created)
        - target_branch: Target branch name or 'root' to switch to
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If navigation fails (at bottom of stack)
    """
    # Navigate down to parent branch
    parent_branch = ctx.branch_manager.get_parent_branch(repo.root, current_branch)
    if parent_branch is None:
        # Check if we're already on trunk
        detected_trunk = ctx.git.detect_trunk_branch(repo.root)
        if current_branch == detected_trunk:
            user_output(f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')")
            raise SystemExit(1)
        else:
            user_output("Error: Could not determine parent branch from Graphite metadata")
            raise SystemExit(1)

    # Check if parent is the trunk - if so, switch to root
    detected_trunk = ctx.git.detect_trunk_branch(repo.root)
    if parent_branch == detected_trunk:
        # Check if trunk is checked out in root (repo.root path)
        trunk_wt_path = ctx.git.find_worktree_for_branch(repo.root, detected_trunk)
        if trunk_wt_path is not None and trunk_wt_path == repo.root:
            # Trunk is in root repository, not in a dedicated worktree
            return "root", False
        else:
            # Trunk has a dedicated worktree
            if trunk_wt_path is None:
                # Auto-create worktree for trunk branch
                _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
                return parent_branch, was_created
            return parent_branch, False
    else:
        # Parent is not trunk, check if it has a worktree
        target_wt_path = ctx.git.find_worktree_for_branch(repo.root, parent_branch)
        if target_wt_path is None:
            # Auto-create worktree for parent branch
            _worktree_path, was_created = ensure_worktree_for_branch(ctx, repo, parent_branch)
            return parent_branch, was_created
        return parent_branch, False
