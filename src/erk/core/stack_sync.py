"""Sync all stack branches with their remote tracking branches.

Provides mechanical stack-wide divergence resolution:
1. Gets the full branch stack
2. Fetches all remote state in one call
3. For each non-trunk branch (bottom-to-top): checks divergence, fixes it
4. Re-tracks all fixed branches with Graphite
5. Restacks the entire stack
6. Returns to the original branch
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.abc import BranchDivergence
from erk_shared.gateway.git.remote_ops.types import PullRebaseError


class BranchSyncAction(Enum):
    ALREADY_SYNCED = "already_synced"
    FAST_FORWARDED = "fast_forwarded"
    REBASED = "rebased"
    SKIPPED_NO_REMOTE = "skipped_no_remote"
    SKIPPED_OTHER_WORKTREE = "skipped_other_worktree"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass(frozen=True)
class BranchSyncResult:
    branch: str
    action: BranchSyncAction
    detail: str


@dataclass(frozen=True)
class StackSyncResult:
    branch_results: tuple[BranchSyncResult, ...]
    restack_success: bool
    restack_error: str | None
    original_branch: str


def sync_stack(ctx: ErkContext, *, repo_root: Path, cwd: Path) -> StackSyncResult:
    """Sync all stack branches with their remote tracking branches.

    Args:
        ctx: ErkContext with gateway dependencies
        repo_root: Path to the git repository root
        cwd: Current working directory

    Returns:
        StackSyncResult with per-branch results, restack status, and original branch.
    """
    # Phase 1: Preparation
    current_branch = ctx.git.branch.get_current_branch(cwd)
    if current_branch is None:
        return StackSyncResult(
            branch_results=(),
            restack_success=False,
            restack_error="Not on a branch (detached HEAD state)",
            original_branch="",
        )

    stack = ctx.branch_manager.get_branch_stack(repo_root, current_branch)
    if stack is None:
        return StackSyncResult(
            branch_results=(),
            restack_success=False,
            restack_error=f"Branch '{current_branch}' is not tracked by Graphite",
            original_branch=current_branch,
        )

    if len(stack) < 2:
        return StackSyncResult(
            branch_results=(),
            restack_success=True,
            restack_error=None,
            original_branch=current_branch,
        )

    # Phase 2: Bulk fetch
    ctx.git.remote.fetch_prune(repo_root, "origin")

    # Phase 3: Per-branch sync (skip trunk, bottom-to-top)
    results: list[BranchSyncResult] = []
    branches_fixed: list[str] = []

    for branch in stack[1:]:
        result = _sync_branch(
            ctx,
            repo_root=repo_root,
            cwd=cwd,
            branch=branch,
            current_branch=current_branch,
        )
        results.append(result)
        if result.action in (BranchSyncAction.FAST_FORWARDED, BranchSyncAction.REBASED):
            branches_fixed.append(branch)

    # Phase 3b: Re-track fixed branches with Graphite
    for branch in branches_fixed:
        ctx.branch_manager.retrack_branch(repo_root, branch)

    # Phase 4: Restack
    restack_success, restack_error = _run_restack(cwd)

    # Phase 5: Return to original branch if needed
    actual_branch = ctx.git.branch.get_current_branch(cwd)
    if actual_branch != current_branch:
        ctx.git.branch.checkout_branch(cwd, current_branch)

    return StackSyncResult(
        branch_results=tuple(results),
        restack_success=restack_success,
        restack_error=restack_error,
        original_branch=current_branch,
    )


def _sync_branch(
    ctx: ErkContext,
    *,
    repo_root: Path,
    cwd: Path,
    branch: str,
    current_branch: str,
) -> BranchSyncResult:
    """Sync a single branch with its remote tracking branch.

    Args:
        ctx: ErkContext with gateway dependencies
        repo_root: Path to the git repository root
        cwd: Current working directory
        branch: Branch name to sync
        current_branch: Currently checked-out branch name

    Returns:
        BranchSyncResult describing what happened.
    """
    # Check remote exists
    has_remote = ctx.git.branch.branch_exists_on_remote(
        repo_root,
        "origin",
        branch,
    )
    if not has_remote:
        return BranchSyncResult(
            branch=branch,
            action=BranchSyncAction.SKIPPED_NO_REMOTE,
            detail="no remote",
        )

    # Check divergence
    divergence = ctx.git.branch.is_branch_diverged_from_remote(cwd, branch, "origin")

    # Already in sync
    if divergence.ahead == 0 and divergence.behind == 0:
        return BranchSyncResult(
            branch=branch,
            action=BranchSyncAction.ALREADY_SYNCED,
            detail="in sync",
        )

    # Ahead only — local is ahead, nothing to incorporate
    if divergence.ahead > 0 and divergence.behind == 0:
        return BranchSyncResult(
            branch=branch,
            action=BranchSyncAction.ALREADY_SYNCED,
            detail=f"{divergence.ahead} ahead",
        )

    # Check if branch is checked out in another worktree
    worktree_path = ctx.git.worktree.is_branch_checked_out(repo_root, branch)
    is_current = branch == current_branch
    is_checked_out_elsewhere = worktree_path is not None and not is_current

    if is_checked_out_elsewhere:
        return BranchSyncResult(
            branch=branch,
            action=BranchSyncAction.SKIPPED_OTHER_WORKTREE,
            detail=f"checked out in {worktree_path}",
        )

    # Behind only — fast-forward
    if divergence.ahead == 0 and divergence.behind > 0:
        return _fast_forward_branch(
            ctx,
            repo_root=repo_root,
            cwd=cwd,
            branch=branch,
            is_current=is_current,
            behind=divergence.behind,
        )

    # Diverged — rebase
    return _rebase_branch(
        ctx,
        repo_root=repo_root,
        cwd=cwd,
        branch=branch,
        is_current=is_current,
        divergence=divergence,
    )


def _fast_forward_branch(
    ctx: ErkContext,
    *,
    repo_root: Path,
    cwd: Path,
    branch: str,
    is_current: bool,
    behind: int,
) -> BranchSyncResult:
    """Fast-forward a branch that is behind its remote."""
    if is_current:
        # Current branch — use pull --rebase
        pull_result = ctx.git.remote.pull_rebase(cwd, "origin", branch)
        if isinstance(pull_result, PullRebaseError):
            return BranchSyncResult(
                branch=branch,
                action=BranchSyncAction.ERROR,
                detail=pull_result.message,
            )
    else:
        # Not checked out — update ref directly
        remote_sha = ctx.git.branch.get_branch_head(
            repo_root,
            f"origin/{branch}",
        )
        if remote_sha is None:
            return BranchSyncResult(
                branch=branch,
                action=BranchSyncAction.ERROR,
                detail="could not resolve origin ref",
            )
        ctx.git.branch.update_local_ref(repo_root, branch, remote_sha)

    return BranchSyncResult(
        branch=branch,
        action=BranchSyncAction.FAST_FORWARDED,
        detail=f"{behind} behind",
    )


def _rebase_branch(
    ctx: ErkContext,
    *,
    repo_root: Path,
    cwd: Path,
    branch: str,
    is_current: bool,
    divergence: BranchDivergence,
) -> BranchSyncResult:
    """Rebase a diverged branch onto its remote."""
    detail = f"{divergence.ahead} ahead, {divergence.behind} behind"

    if is_current:
        return _rebase_current_branch(ctx, cwd=cwd, branch=branch, detail=detail)

    # Not checked out — checkout, rebase, checkout back
    original_branch = ctx.git.branch.get_current_branch(cwd)
    ctx.git.branch.checkout_branch(cwd, branch)

    result = _rebase_current_branch(ctx, cwd=cwd, branch=branch, detail=detail)

    # Checkout back to original branch
    if original_branch is not None:
        ctx.git.branch.checkout_branch(cwd, original_branch)

    return result


def _rebase_current_branch(
    ctx: ErkContext,
    *,
    cwd: Path,
    branch: str,
    detail: str,
) -> BranchSyncResult:
    """Rebase the currently checked-out branch via pull --rebase."""
    pull_result = ctx.git.remote.pull_rebase(cwd, "origin", branch)
    if isinstance(pull_result, PullRebaseError):
        # Check if rebase is in progress and abort
        if ctx.git.rebase.is_rebase_in_progress(cwd):
            ctx.git.rebase.rebase_abort(cwd)
        return BranchSyncResult(branch=branch, action=BranchSyncAction.CONFLICT, detail=detail)
    return BranchSyncResult(branch=branch, action=BranchSyncAction.REBASED, detail=detail)


def _run_restack(cwd: Path) -> tuple[bool, str | None]:
    """Run gt restack --no-interactive.

    Returns:
        Tuple of (success, error_message).
    """
    result = subprocess.run(
        ["gt", "restack", "--no-interactive"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return (True, None)
    return (False, result.stderr.strip() or "gt restack failed")
