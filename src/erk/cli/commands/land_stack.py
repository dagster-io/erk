"""Stack landing logic for `erk land --stack`.

Lands an entire Graphite stack bottom-up: validate all PRs, then merge
each from the bottom, rebasing upstack branches between iterations.

This module is separate from land_cmd.py because the stack loop is
fundamentally different from the single-PR pipeline pattern.
"""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.commands.land_cmd import check_unresolved_comments
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    run_objective_update_after_land,
)
from erk.cli.commands.wt.delete_cmd import _prune_worktrees_safe
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.github.types import MergeError, PRDetails, PRNotFound
from erk_shared.output.output import user_output


@dataclass(frozen=True)
class StackLandEntry:
    """Pre-validated entry for a single branch in a stack land operation."""

    branch: str
    pr_number: int
    pr_details: PRDetails
    worktree_path: Path | None
    plan_id: str | None
    objective_number: int | None


def execute_land_stack(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    force: bool,
    pull_flag: bool,
    no_delete: bool,
    skip_learn: bool,
) -> None:
    """Land an entire Graphite stack bottom-up.

    Algorithm:
    1. Resolve stack from current branch
    2. Pre-validate all PRs (fail fast before mutations)
    3. Display summary
    4. For each branch bottom-up: rebase, re-parent upstack, merge, delete remote
    5. Post-land cleanup

    Args:
        ctx: ErkContext
        repo: Repository context
        force: Skip confirmation prompts
        pull_flag: Pull trunk after landing
        no_delete: Preserve local branches after landing
        skip_learn: Skip creating learn plans
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Step 1: Resolve stack
    branches_to_land = _resolve_stack(ctx, main_repo_root)

    # Step 2: Pre-validate all PRs
    trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)
    entries = _validate_stack_prs(ctx, main_repo_root, branches_to_land, trunk, force=force)

    # Step 3: Display summary
    _display_stack_summary(entries)

    # Step 4: Handle dry-run
    if ctx.dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Step 5: Land each branch bottom-up
    total = len(entries)
    for i, entry in enumerate(entries):
        # Rebase onto trunk if not the first branch
        if i > 0:
            _rebase_and_push(ctx, main_repo_root, entry.branch, trunk)

        # Re-parent remaining upstack PRs to trunk
        remaining = entries[i + 1 :]
        if remaining:
            _reparent_upstack(ctx, main_repo_root, remaining, trunk)

        # Merge and cleanup remote branch
        _merge_and_cleanup_branch(ctx, main_repo_root, entry)

        user_output(
            click.style("✓", fg="green")
            + f" Merged PR #{entry.pr_number} [{entry.branch}] ({i + 1}/{total})"
        )

    # Step 6: Post-land cleanup
    if not no_delete:
        _cleanup_after_stack_land(ctx, repo, entries, main_repo_root)

    # Step 7: Pull trunk
    if pull_flag:
        _pull_trunk(ctx, main_repo_root, trunk)

    # Step 8: Objective updates (fail-open)
    for entry in entries:
        if entry.objective_number is not None:
            run_objective_update_after_land(
                ctx,
                objective=entry.objective_number,
                pr=entry.pr_number,
                branch=entry.branch,
                plan=int(entry.plan_id) if entry.plan_id is not None else None,
                worktree_path=main_repo_root,
            )

    user_output(
        click.style("\n✓", fg="green", bold=True)
        + f" Stack landed: {total} PR(s) merged successfully"
    )
    raise SystemExit(0)


def _resolve_stack(ctx: ErkContext, main_repo_root: Path) -> list[str]:
    """Get stack branches to land (excluding trunk).

    Returns:
        List of branch names to land, ordered bottom-up (closest to trunk first).
    """
    Ensure.invariant(
        ctx.branch_manager.is_graphite_managed(),
        "--stack requires Graphite for stack tracking.\n\n"
        "To enable Graphite: erk config set use_graphite true",
    )

    current_branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(ctx.cwd),
        "Not currently on a branch (detached HEAD).",
    )

    stack = ctx.branch_manager.get_branch_stack(main_repo_root, current_branch)
    Ensure.invariant(
        stack is not None,
        f"Branch '{current_branch}' is not in a Graphite stack.\n"
        "Use 'erk land' without --stack for non-stacked branches.",
    )
    # Type narrowing after Ensure.invariant
    assert stack is not None

    # Stack is [trunk, branch1, branch2, ...] — strip trunk
    Ensure.invariant(
        len(stack) >= 2,
        f"Stack has no branches to land (only contains trunk '{stack[0]}').",
    )

    return stack[1:]


def _validate_stack_prs(
    ctx: ErkContext,
    main_repo_root: Path,
    branches: list[str],
    trunk: str,
    *,
    force: bool,
) -> list[StackLandEntry]:
    """Pre-validate all PRs in the stack before any mutations.

    Checks each PR is open, has the expected base, and has no unresolved comments.

    Returns:
        List of StackLandEntry objects, one per branch.
    """
    entries: list[StackLandEntry] = []

    for branch in branches:
        pr_result = ctx.github.get_pr_for_branch(main_repo_root, branch)
        Ensure.invariant(
            not isinstance(pr_result, PRNotFound),
            f"No pull request found for branch '{branch}' in the stack.",
        )
        # Type narrowing
        assert isinstance(pr_result, PRDetails)

        Ensure.invariant(
            pr_result.state == "OPEN",
            f"PR #{pr_result.number} for branch '{branch}' is not open "
            f"(state: {pr_result.state}).\n"
            "All PRs in the stack must be open to land.",
        )

        # Check unresolved comments (respects --force)
        check_unresolved_comments(ctx, main_repo_root, pr_result.number, force=force)

        # Resolve plan and objective context
        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, branch)
        objective_number = get_objective_for_branch(ctx, main_repo_root, branch)

        # Find worktree for this branch (may be None)
        worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)

        entries.append(
            StackLandEntry(
                branch=branch,
                pr_number=pr_result.number,
                pr_details=pr_result,
                worktree_path=worktree_path,
                plan_id=plan_id,
                objective_number=objective_number,
            )
        )

    return entries


def _display_stack_summary(entries: list[StackLandEntry]) -> None:
    """Display numbered list of PRs to be landed."""
    user_output(f"\nLanding {len(entries)} PR(s) bottom-up:\n")
    for i, entry in enumerate(entries, 1):
        user_output(f"  {i}. PR #{entry.pr_number} [{entry.branch}] — {entry.pr_details.title}")
    user_output("")


def _resolve_rebase_cwd(
    ctx: ErkContext,
    main_repo_root: Path,
    branch: str,
) -> Path:
    """Find the directory to run rebase in for a given branch.

    Checks for existing worktree first, falls back to checking out in root.

    Returns:
        Path to use as cwd for rebase operations.
    """
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)
    if worktree_path is not None:
        return worktree_path

    # No worktree — checkout branch in root worktree
    ctx.branch_manager.checkout_branch(main_repo_root, branch)
    return main_repo_root


def _rebase_and_push(
    ctx: ErkContext,
    main_repo_root: Path,
    branch: str,
    trunk: str,
) -> None:
    """Fetch updated trunk, rebase branch onto it, and force-push.

    Bails with error if rebase has conflicts.
    """
    # Fetch latest trunk
    ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk)

    # Find where to run rebase
    cwd = _resolve_rebase_cwd(ctx, main_repo_root, branch)

    # Rebase onto updated trunk
    result = ctx.git.rebase.rebase_onto(cwd, f"origin/{trunk}")
    if not result.success:
        # Abort the conflicting rebase
        ctx.git.rebase.rebase_abort(cwd)
        conflict_list = (
            ", ".join(result.conflict_files) if result.conflict_files else "unknown files"
        )
        Ensure.invariant(
            False,
            f"Rebase conflicts on branch '{branch}': {conflict_list}\n\n"
            f"Resolve conflicts manually:\n"
            f"  cd {cwd}\n"
            f"  git rebase origin/{trunk}\n"
            "  # resolve conflicts\n"
            "  erk land --stack  # retry",
        )

    # Force-push the rebased branch
    ctx.git.remote.push_to_remote(cwd, "origin", branch, set_upstream=False, force=True)


def _reparent_upstack(
    ctx: ErkContext,
    main_repo_root: Path,
    remaining_entries: list[StackLandEntry],
    trunk: str,
) -> None:
    """Update PR base branches and Graphite tracking for remaining upstack PRs.

    This must happen BEFORE merging to prevent GitHub from auto-closing
    child PRs when the parent branch is deleted.
    """
    for entry in remaining_entries:
        ctx.github.update_pr_base_branch(main_repo_root, entry.pr_number, trunk)
        ctx.branch_manager.track_branch(main_repo_root, entry.branch, trunk)


def _merge_and_cleanup_branch(
    ctx: ErkContext,
    main_repo_root: Path,
    entry: StackLandEntry,
) -> None:
    """Squash-merge a PR and delete its remote branch."""
    merge_result = ctx.github.merge_pr(
        main_repo_root,
        entry.pr_number,
        squash=True,
        verbose=False,
        subject=f"{entry.pr_details.title} (#{entry.pr_number})",
        body=entry.pr_details.body,
    )
    Ensure.invariant(
        not isinstance(merge_result, MergeError),
        f"Failed to merge PR #{entry.pr_number} [{entry.branch}]: "
        + (merge_result.message if isinstance(merge_result, MergeError) else ""),
    )

    ctx.github.delete_remote_branch(main_repo_root, entry.branch)


def _cleanup_after_stack_land(
    ctx: ErkContext,
    repo: RepoContext,
    entries: list[StackLandEntry],
    main_repo_root: Path,
) -> None:
    """Delete local branches and worktrees for all landed stack entries."""
    trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)

    # First, ensure we're on trunk in the root worktree
    ctx.branch_manager.checkout_branch(main_repo_root, trunk)

    local_branches = ctx.git.branch.list_local_branches(main_repo_root)

    for entry in entries:
        # Detach any worktree that has this branch checked out
        worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, entry.branch)
        if worktree_path is not None:
            ctx.branch_manager.checkout_detached(worktree_path, trunk)

        # Delete local branch if it exists
        if entry.branch in local_branches:
            ctx.branch_manager.delete_branch(main_repo_root, entry.branch, force=True)

    # Prune stale worktree references
    _prune_worktrees_safe(ctx.git, main_repo_root)


def _pull_trunk(ctx: ErkContext, main_repo_root: Path, trunk: str) -> None:
    """Pull latest trunk after landing."""
    ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk)
    divergence = ctx.git.branch.is_branch_diverged_from_remote(main_repo_root, trunk, "origin")
    if divergence.behind > 0 and not divergence.is_diverged:
        user_output(f"Pulling latest changes from origin/{trunk}...")
        try:
            ctx.git.remote.pull_branch(main_repo_root, "origin", trunk, ff_only=True)
        except RuntimeError:
            user_output(
                click.style("Warning: ", fg="yellow") + "git pull failed (try running manually)"
            )
