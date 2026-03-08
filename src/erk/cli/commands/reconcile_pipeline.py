"""Detection and processing pipeline for reconciling merged branches.

Detects branches whose remote tracking refs have been pruned (gone=True)
and whose PRs are in MERGED state. For each, runs post-merge lifecycle
operations: learn PR creation, objective update, and branch/worktree cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from erk.cli.commands.land_cmd import _ensure_branch_not_checked_out
from erk.cli.commands.land_learn import _create_learn_pr_for_merged_branch
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    run_objective_update_after_land,
)
from erk.cli.commands.slot.common import find_branch_assignment
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.cli.commands.wt.delete_cmd import _prune_worktrees_safe
from erk.core.context import ErkContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.context.types import RepoContext
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.output.output import user_output

logger = logging.getLogger(__name__)

StepStatus = Literal["done", "skipped", "failed"]


@dataclass(frozen=True)
class StepResult:
    """Result of a single reconciliation step (learn, objective, label, cleanup)."""

    status: StepStatus
    reason: str | None  # Required for skipped/failed, None for done


def step_done() -> StepResult:
    """Create a StepResult indicating success."""
    return StepResult(status="done", reason=None)


def step_skipped(*, reason: str) -> StepResult:
    """Create a StepResult indicating the step was skipped with a reason."""
    return StepResult(status="skipped", reason=reason)


def step_failed(*, reason: str) -> StepResult:
    """Create a StepResult indicating the step failed with a reason."""
    return StepResult(status="failed", reason=reason)


_LEARN_SKIP_REASONS: dict[str, str] = {
    "skipped_no_material": "no session material found",
    "skipped_erk_learn": "plan is an erk-learn (cycle prevention)",
    "skipped_already_exists": "learn plan already exists",
    "skipped_config_disabled": "learn plans disabled in config",
}


@dataclass(frozen=True)
class ReconcileBranchInfo:
    """Information about a branch whose remote tracking ref is gone and PR is merged."""

    branch: str
    pr_number: int
    pr_title: str | None
    worktree_path: Path | None
    plan_id: str | None
    objective_number: int | None


@dataclass(frozen=True)
class ReconcileResult:
    """Result of processing a single merged branch with per-step detail."""

    branch: str
    pr_number: int
    learn: StepResult
    objective: StepResult
    label: StepResult
    cleanup: StepResult

    @property
    def has_failure(self) -> bool:
        """True if any step failed."""
        steps = (self.learn, self.objective, self.label, self.cleanup)
        return any(s.status == "failed" for s in steps)


def detect_merged_branches(
    ctx: ErkContext,
    *,
    repo_root: Path,
    main_repo_root: Path,
) -> list[ReconcileBranchInfo]:
    """Detect local branches whose remote tracking refs are gone and PRs are merged.

    Steps:
    1. Fetch with prune to update remote refs
    2. Get all branch sync info and filter for gone=True
    3. Exclude trunk branch
    4. For each candidate, check PR state via GitHub
    5. For confirmed merged, resolve plan/objective/worktree metadata

    Args:
        ctx: ErkContext
        repo_root: Working tree root
        main_repo_root: Main repository root (for metadata paths)

    Returns:
        List of ReconcileBranchInfo for branches confirmed merged on GitHub.
    """
    # 1. Fetch and prune
    ctx.git.remote.fetch_prune(repo_root, "origin")

    # 2. Get sync info and filter for gone branches
    sync_info = ctx.git.branch.get_all_branch_sync_info(repo_root)
    gone_branches = [info for info in sync_info.values() if info.gone]

    if not gone_branches:
        return []

    # 3. Exclude trunk
    trunk = ctx.git.branch.detect_trunk_branch(repo_root)
    candidates = [info for info in gone_branches if info.branch != trunk]

    if not candidates:
        return []

    # 4. Check PR state for each candidate
    merged: list[ReconcileBranchInfo] = []
    for info in candidates:
        pr_result = ctx.github.get_pr_for_branch(main_repo_root, info.branch)
        if isinstance(pr_result, PRNotFound):
            continue
        if pr_result.state != "MERGED":
            continue

        # 5. Resolve metadata
        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, info.branch)
        objective_number = get_objective_for_branch(ctx, main_repo_root, info.branch)
        worktree_path = ctx.git.worktree.find_worktree_for_branch(repo_root, info.branch)

        merged.append(
            ReconcileBranchInfo(
                branch=info.branch,
                pr_number=pr_result.number,
                pr_title=pr_result.title,
                worktree_path=worktree_path,
                plan_id=plan_id,
                objective_number=objective_number,
            )
        )

    return merged


def process_merged_branch(
    ctx: ErkContext,
    info: ReconcileBranchInfo,
    *,
    main_repo_root: Path,
    repo: RepoContext,
    cwd: Path,
    dry_run: bool,
    skip_learn: bool,
) -> ReconcileResult:
    """Process a single merged branch: learn PR, objective update, label, cleanup.

    Each step is fail-open: errors on one step don't prevent the next.

    Args:
        ctx: ErkContext
        info: Branch info from detection
        main_repo_root: Main repository root
        repo: RepoContext for pool operations
        cwd: Current working directory
        dry_run: If True, skip all mutations
        skip_learn: If True, skip learn PR creation

    Returns:
        ReconcileResult with per-step outcomes.
    """
    dry_skip = step_skipped(reason="dry run")
    if dry_run:
        return ReconcileResult(
            branch=info.branch,
            pr_number=info.pr_number,
            learn=dry_skip,
            objective=dry_skip,
            label=dry_skip,
            cleanup=dry_skip,
        )

    # 1. Learn PR (fail-open)
    learn = _run_learn_step(
        ctx,
        info=info,
        main_repo_root=main_repo_root,
        cwd=cwd,
        skip_learn=skip_learn,
    )

    # 2. Objective update (fail-open)
    objective = _run_objective_step(ctx, info=info, cwd=cwd)

    # 3. Label (not yet implemented — Phase 2)
    label = step_skipped(reason="label stamping not yet implemented")

    # 4. Cleanup: unassign slot, delete branch, remove worktree
    cleanup = _run_cleanup_step(ctx, info=info, main_repo_root=main_repo_root, repo=repo)

    return ReconcileResult(
        branch=info.branch,
        pr_number=info.pr_number,
        learn=learn,
        objective=objective,
        label=label,
        cleanup=cleanup,
    )


def _run_learn_step(
    ctx: ErkContext,
    *,
    info: ReconcileBranchInfo,
    main_repo_root: Path,
    cwd: Path,
    skip_learn: bool,
) -> StepResult:
    """Run the learn PR creation step."""
    if skip_learn:
        return step_skipped(reason="--skip-learn flag")
    if info.plan_id is None:
        return step_skipped(reason="no linked plan")
    try:
        outcome = _create_learn_pr_for_merged_branch(
            ctx,
            plan_id=info.plan_id,
            merged_pr_number=info.pr_number,
            main_repo_root=main_repo_root,
            cwd=cwd,
        )
        if outcome == "created":
            return step_done()
        skip_reason = _LEARN_SKIP_REASONS.get(outcome, outcome)
        return step_skipped(reason=skip_reason)
    except Exception as exc:
        user_output(
            click.style("Warning: ", fg="yellow") + f"Learn PR failed for {info.branch}: {exc}"
        )
        return step_failed(reason=str(exc))


def _run_objective_step(
    ctx: ErkContext,
    *,
    info: ReconcileBranchInfo,
    cwd: Path,
) -> StepResult:
    """Run the objective update step."""
    if info.objective_number is None:
        return step_skipped(reason="no linked objective")
    try:
        run_objective_update_after_land(
            ctx,
            objective=info.objective_number,
            pr=info.pr_number,
            branch=info.branch,
            worktree_path=cwd,
        )
        return step_done()
    except Exception as exc:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Objective update failed for {info.branch}: {exc}"
        )
        return step_failed(reason=str(exc))


def _run_cleanup_step(
    ctx: ErkContext,
    *,
    info: ReconcileBranchInfo,
    main_repo_root: Path,
    repo: RepoContext,
) -> StepResult:
    """Run the branch/worktree cleanup step."""
    try:
        _cleanup_branch(ctx, info=info, main_repo_root=main_repo_root, repo=repo)
        return step_done()
    except Exception as exc:
        msg = f"Cleanup failed for {info.branch}: {exc}"
        user_output(click.style("Warning: ", fg="yellow") + msg)
        return step_failed(reason=str(exc))


def _cleanup_branch(
    ctx: ErkContext,
    *,
    info: ReconcileBranchInfo,
    main_repo_root: Path,
    repo: RepoContext,
) -> None:
    """Clean up a merged branch: unassign slot, delete branch, remove worktree."""
    # Check if branch exists locally before trying to clean up
    local_branches = ctx.git.branch.list_local_branches(main_repo_root)
    if info.branch not in local_branches:
        return

    # Unassign slot if applicable
    pool_json_path = repo.repo_dir / "pool.json"
    pool_state = load_pool_state(pool_json_path)
    if pool_state is not None:
        assignment = find_branch_assignment(pool_state, info.branch)
        if assignment is not None:
            execute_unassign(ctx, repo, pool_state, assignment)

    # Ensure branch is not checked out anywhere
    _ensure_branch_not_checked_out(ctx, repo_root=main_repo_root, branch=info.branch)

    # Delete branch
    ctx.branch_manager.delete_branch(main_repo_root, info.branch, force=True)

    # Remove worktree if it exists and is a linked (non-root) worktree
    if info.worktree_path is not None and info.worktree_path != main_repo_root:
        ctx.git.worktree.safe_chdir(main_repo_root)
        ctx.git.worktree.remove_worktree(main_repo_root, info.worktree_path, force=True)
        _prune_worktrees_safe(ctx.git, main_repo_root)
