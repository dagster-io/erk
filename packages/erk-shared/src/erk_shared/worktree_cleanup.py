"""Shared helpers for worktree cleanup operations.

These functions operate on branches, PRs, and plans - not slot-specific.
Used by both `erk wt delete` and `erk slot unassign` commands.
"""

import subprocess
from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.gateway.github.metadata.schemas import WORKTREE_NAME
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.output.output import user_output
from erk_shared.pr_store.conversion import header_str
from erk_shared.pr_store.types import PlanQuery, PlanState


def get_pr_info_for_branch(ctx: ErkContext, repo_root: Path, branch: str) -> tuple[int, str] | None:
    """Get PR info for display during planning phase.

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

    Args:
        ctx: Erk context with plan store
        repo_root: Repository root directory
        worktree_name: Name of the worktree to find a plan for

    Returns:
        Tuple of (PR number, state) if found, None otherwise.
    """
    # Search ALL states (open and closed) to find the plan
    query = PlanQuery(labels=["erk-pr"])
    plans = ctx.plan_store.list_managed_prs(repo_root, query)

    for plan in plans:
        plan_worktree_name = header_str(plan.header_fields, WORKTREE_NAME)
        if plan_worktree_name == worktree_name:
            return (int(plan.pr_identifier), plan.state)

    return None


def close_pr_for_branch(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
) -> int | None:
    """Close the PR associated with a branch if it exists and is open.

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

    Args:
        ctx: Erk context with plan store
        repo_root: Repository root directory
        worktree_name: Name of the worktree to find a plan for

    Returns:
        PR number if closed, None otherwise
    """
    plan_info = get_plan_info_for_worktree(ctx, repo_root, worktree_name)

    if plan_info is None:
        user_output(click.style("ℹ️  ", fg="blue", bold=True) + "No associated plan found")
        return None

    pr_number, state = plan_info
    if state == PlanState.CLOSED:
        user_output(click.style("ℹ️  ", fg="blue", bold=True) + f"PR #{pr_number} already closed")
        return None

    ctx.plan_store.close_managed_pr(repo_root, str(pr_number))
    user_output(click.style("ℹ️  ", fg="blue", bold=True) + f"Closed PR #{pr_number}")
    return pr_number


def delete_branch(
    ctx: ErkContext, *, repo_root: Path, branch: str, force: bool, dry_run: bool
) -> None:
    """Delete a branch after its worktree has been removed.

    This function encapsulates a legitimate error boundary because:
    1. `gt delete` prompts for user confirmation, which can be declined (exit 1)
    2. `git branch -d` may fail if branch is not fully merged
    3. There's no LBYL way to predict user's response to interactive prompt
    4. This is a CLI error boundary - appropriate place per AGENTS.md

    The exception handling distinguishes between user-declined (expected) and
    actual errors (propagated as SystemExit).

    Note: run_subprocess_with_context catches CalledProcessError and re-raises
    as RuntimeError with the original exception in __cause__.

    Uses BranchManager abstraction to handle both Graphite and Git paths transparently.

    Args:
        ctx: Erk context with branch manager
        repo_root: Repository root directory
        branch: Branch name to delete
        force: Whether to force deletion (skip merge check)
        dry_run: Whether this is a dry run

    Raises:
        SystemExit: If branch deletion fails with unexpected error
    """
    try:
        ctx.branch_manager.delete_branch(repo_root, branch, force=force)
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
