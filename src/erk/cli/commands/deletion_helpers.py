"""Shared helpers for deletion operations across CLI commands.

This module provides reusable functions for:
- Branch deletion with Graphite awareness
- Worktree deletion (slot-aware)
- PR and plan closing
- Shell safety (escaping worktrees)

Use these helpers when implementing delete/cleanup commands.
"""

import shutil
import subprocess
from pathlib import Path

import click

from erk.cli.commands.navigation_helpers import find_assignment_by_worktree_path
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.core.context import ErkContext, regenerate_context
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import load_pool_state
from erk.core.worktree_utils import find_worktree_containing_path
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.git.abc import Git
from erk_shared.github.metadata.plan_header import extract_plan_header_worktree_name
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanQuery, PlanState


def get_pr_info_for_branch(ctx: ErkContext, repo_root: Path, branch: str) -> tuple[int, str] | None:
    """Get PR info for display during planning phase.

    Use this function when displaying planned operations to show what
    will happen to the associated PR.

    Args:
        ctx: Erk context with GitHub operations
        repo_root: Repository root directory
        branch: Branch name to find PR for

    Returns:
        Tuple of (PR number, state) if found, None otherwise.
        State is one of: "OPEN", "CLOSED", "MERGED"
    """
    pr = ctx.github.get_pr_for_branch(repo_root, branch)
    if isinstance(pr, PRNotFound):
        return None
    return (pr.number, pr.state)


def get_plan_info_for_worktree(
    ctx: ErkContext, repo_root: Path, worktree_name: str
) -> tuple[int, PlanState] | None:
    """Find a plan associated with a worktree name (any state).

    Use this function when displaying planned operations to show what
    will happen to the associated plan.

    Args:
        ctx: Erk context with plan store
        repo_root: Repository root directory
        worktree_name: Name of the worktree to find a plan for

    Returns:
        Tuple of (plan number, state) if found, None otherwise.
    """
    # Search ALL states (open and closed) to find the plan
    query = PlanQuery(labels=["erk-plan"])
    plans = ctx.plan_store.list_plans(repo_root, query)

    for plan in plans:
        plan_worktree_name = extract_plan_header_worktree_name(plan.body)
        if plan_worktree_name == worktree_name:
            return (int(plan.plan_identifier), plan.state)

    return None


def close_pr_for_branch(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
) -> int | None:
    """Close the PR associated with a branch if it exists and is open.

    Use this function when cleaning up a branch to also close its PR.
    Reports to user what action was taken.

    Args:
        ctx: Erk context with GitHub operations
        repo_root: Repository root directory
        branch: Branch name to find PR for

    Returns:
        PR number if closed, None otherwise
    """
    pr = ctx.github.get_pr_for_branch(repo_root, branch)

    if isinstance(pr, PRNotFound):
        return None

    if pr.state == "OPEN":
        ctx.github.close_pr(repo_root, pr.number)
        user_output(
            click.style("ℹ️  ", fg="blue", bold=True)
            + f"Closed PR #{pr.number}: {click.style(pr.title, fg='cyan')}"
        )
        return pr.number

    # PR exists but is already closed/merged
    state_color = "green" if pr.state == "MERGED" else "yellow"
    user_output(
        click.style("ℹ️  ", fg="blue", bold=True)
        + f"PR #{pr.number} already {click.style(pr.state.lower(), fg=state_color)}"
    )
    return None


def close_plan_for_worktree(
    ctx: ErkContext,
    repo_root: Path,
    worktree_name: str,
) -> int | None:
    """Close the plan associated with a worktree name if it exists and is open.

    Use this function when deleting a worktree to also close its plan.
    Reports to user what action was taken.

    Args:
        ctx: Erk context with plan store
        repo_root: Repository root directory
        worktree_name: Name of the worktree to find a plan for

    Returns:
        Plan issue number if closed, None otherwise
    """
    plan_info = get_plan_info_for_worktree(ctx, repo_root, worktree_name)

    if plan_info is None:
        user_output(click.style("ℹ️  ", fg="blue", bold=True) + "No associated plan found")
        return None

    plan_number, state = plan_info
    if state == PlanState.CLOSED:
        user_output(
            click.style("ℹ️  ", fg="blue", bold=True) + f"Plan #{plan_number} already closed"
        )
        return None

    ctx.plan_store.close_plan(repo_root, str(plan_number))
    user_output(click.style("ℹ️  ", fg="blue", bold=True) + f"Closed plan #{plan_number}")
    return plan_number


def try_git_worktree_delete(git_ops: Git, repo_root: Path, wt_path: Path) -> bool:
    """Attempt git worktree remove, returning success status.

    Use this function for the first attempt at worktree deletion.
    If this fails, manual cleanup with shutil.rmtree may be needed.

    This function violates LBYL norms because there's no reliable way to
    check a priori if git worktree remove will succeed. The worktree might be:
    - Already removed from git metadata
    - In a partially corrupted state
    - Referenced by stale lock files

    Git's own error handling is unreliable for these edge cases, so we use
    try/except as an error boundary and rely on manual cleanup + prune.

    Args:
        git_ops: Git gateway for operations
        repo_root: Repository root directory
        wt_path: Path to the worktree to remove

    Returns:
        True if git removal succeeded, False otherwise
    """
    try:
        git_ops.remove_worktree(repo_root, wt_path, force=True)
        return True
    except Exception:
        # Git removal failed - manual cleanup will handle it
        return False


def prune_worktrees_safe(git_ops: Git, repo_root: Path) -> None:
    """Prune worktree metadata, ignoring errors if nothing to prune.

    Use this function after manual worktree deletion to clean up git's
    internal state.

    This function violates LBYL norms because git worktree prune can fail
    for various reasons (no stale worktrees, permission issues, etc.) that
    are not easily detectable beforehand. Since pruning is a cleanup operation
    and failure doesn't affect the primary operation, we allow silent failure.

    Args:
        git_ops: Git gateway for operations
        repo_root: Repository root directory
    """
    try:
        git_ops.prune_worktrees(repo_root)
    except Exception:
        # Prune might fail if there's nothing to prune or other non-critical issues
        pass


def escape_worktree_if_inside(
    ctx: ErkContext, repo_root: Path, wt_path: Path, dry_run: bool
) -> ErkContext:
    """Change to repository root if currently inside the worktree being deleted.

    Use this function before deleting a worktree to prevent the shell from
    being left in a deleted directory.

    Args:
        ctx: Erk context (may be regenerated if cwd changes)
        repo_root: Repository root to escape to
        wt_path: Path to the worktree being deleted
        dry_run: Whether in dry-run mode (skip actual chdir)

    Returns:
        New context if directory was changed (context is immutable),
        otherwise returns the original context.
    """
    if not ctx.git.path_exists(ctx.cwd):
        return ctx

    current_dir = ctx.cwd.resolve()
    worktrees = ctx.git.list_worktrees(repo_root)
    current_worktree_path = find_worktree_containing_path(worktrees, current_dir)

    if current_worktree_path is None:
        return ctx

    if current_worktree_path.resolve() != wt_path.resolve():
        return ctx

    # Change to repository root before deletion
    user_output(
        click.style("ℹ️  ", fg="blue", bold=True)
        + f"Changing directory to repository root: {click.style(str(repo_root), fg='cyan')}"
    )

    # Change directory using safe_chdir which handles both real and sentinel paths
    if not dry_run and ctx.git.safe_chdir(repo_root):
        # Regenerate context with new cwd (context is immutable)
        return regenerate_context(ctx)

    return ctx


def delete_worktree_directory(ctx: ErkContext, repo: RepoContext, wt_path: Path) -> bool:
    """Delete the worktree directory from filesystem (slot-aware).

    Use this function for the main worktree deletion operation.

    If worktree is a pool slot: unassigns slot (keeps directory for reuse).
    If not a pool slot: removes worktree directory.

    First attempts git worktree remove, then manually deletes if still present.
    This function encapsulates the legitimate error boundary for shutil.rmtree
    because in pure test mode, the path may be a sentinel that doesn't exist
    on the real filesystem.

    Args:
        ctx: Erk context with git operations
        repo: Repository context with worktree pool info
        wt_path: Path to the worktree to delete

    Returns:
        True if this was a slot worktree (slot was unassigned), False otherwise.
    """
    # Check if this is a slot worktree
    state = load_pool_state(repo.pool_json_path)
    assignment = None
    if state is not None:
        assignment = find_assignment_by_worktree_path(state, wt_path)

    if assignment is not None:
        # Slot worktree: unassign instead of delete
        # state is guaranteed to be non-None since assignment was found in it
        assert state is not None
        execute_unassign(ctx, repo, state, assignment)
        user_output(
            click.style("✓", fg="green")
            + f" Unassigned slot {click.style(assignment.slot_name, fg='cyan')}"
        )
        return True

    # Non-slot worktree: delete normally
    # Try to delete via git first - this updates git's metadata when possible
    try_git_worktree_delete(ctx.git, repo.root, wt_path)

    # Always manually delete directory if it still exists
    if not ctx.git.path_exists(wt_path):
        return False

    if ctx.dry_run:
        user_output(f"[DRY RUN] Would delete directory: {wt_path}")
        return False

    # Only call shutil.rmtree() if we're on a real filesystem.
    # In pure test mode, we skip the actual deletion since it's a sentinel path.
    # This violates LBYL because there's no reliable way to distinguish sentinel
    # paths from real paths that have been deleted between the path_exists check
    # and the rmtree call (race condition).
    try:
        shutil.rmtree(wt_path)
    except OSError:
        # Path doesn't exist on real filesystem (sentinel path), skip deletion
        pass

    # Prune worktree metadata to clean up any stale references
    prune_worktrees_safe(ctx.git, repo.root)
    return False


def delete_branch_at_error_boundary(
    ctx: ErkContext,
    *,
    repo_root: Path,
    branch: str,
    force: bool,
    dry_run: bool,
    graphite: Graphite,
) -> None:
    """Delete a branch with Graphite awareness and proper error handling.

    Use this function when deleting branches that may be:
    - Tracked by Graphite (uses `gt delete`)
    - Not tracked (uses `git branch -d/-D`)

    Handles user-declined prompts gracefully (not treated as errors).

    This function encapsulates a legitimate error boundary because:
    1. `gt delete` prompts for user confirmation, which can be declined (exit 1)
    2. `git branch -d` may fail if branch is not fully merged
    3. There's no LBYL way to predict user's response to interactive prompt
    4. This is a CLI error boundary - appropriate place per AGENTS.md

    The exception handling distinguishes between user-declined (expected) and
    actual errors (propagated as SystemExit).

    Note: run_subprocess_with_context catches CalledProcessError and re-raises
    as RuntimeError with the original exception in __cause__.

    Args:
        ctx: ErkContext with git operations
        repo_root: Repository root for branch operations
        branch: Branch name to delete
        force: Use -D (force) instead of -d
        dry_run: Print what would be done without executing
        graphite: Graphite gateway for tracking checks
    """
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Determine if branch is tracked by Graphite (LBYL check using gt branch info)
    branch_is_tracked = False
    if use_graphite:
        branch_is_tracked = graphite.is_branch_tracked(repo_root, branch)

    try:
        if branch_is_tracked:
            ctx.git.delete_branch_with_graphite(repo_root, branch, force=force)
        else:
            ctx.git.delete_branch(repo_root, branch, force=force)
        if not dry_run:
            branch_text = click.style(branch, fg="green")
            user_output(f"✅ Deleted branch: {branch_text}")
    except RuntimeError as e:
        _handle_branch_deletion_error(e, branch, force)


def _handle_branch_deletion_error(e: RuntimeError, branch: str, force: bool) -> None:
    """Handle errors from branch deletion commands.

    This function encapsulates the error boundary logic for branch deletion.
    Exit code 1 with --force off typically means user declined the confirmation
    prompt, which is expected behavior. Other errors are propagated as SystemExit.

    Args:
        e: RuntimeError from run_subprocess_with_context, with the original
           CalledProcessError accessible via e.__cause__
        branch: Name of the branch that failed to delete
        force: Whether --force flag was used
    """
    branch_text = click.style(branch, fg="yellow")

    # Extract returncode from the original CalledProcessError in __cause__
    returncode: int | None = None
    if isinstance(e.__cause__, subprocess.CalledProcessError):
        returncode = e.__cause__.returncode

    if returncode == 1 and not force:
        # User declined - this is expected behavior, not an error
        user_output(f"⭕ Skipped deletion of branch: {branch_text} (user declined or not eligible)")
    else:
        # Other error (branch doesn't exist, git failure, etc.)
        # The RuntimeError message already contains stderr from run_subprocess_with_context
        user_output(
            click.style("Error: ", fg="red") + f"Failed to delete branch {branch_text}: {e}"
        )
        raise SystemExit(1) from e
