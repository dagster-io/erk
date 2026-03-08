"""Stack landing for Graphite stacks.

Implements bottom-up landing of an entire Graphite stack: resolve the stack,
validate all PRs, confirm with the user, then iterate through each branch
rebasing, re-parenting the next entry, and merging.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk.cli.commands.land_learn import _create_learn_pr_core
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    run_objective_update_after_land,
)
from erk.cli.ensure import Ensure, UserFacingCliError
from erk_shared.gateway.github.types import MergeError, PRDetails
from erk_shared.output.output import user_output

if TYPE_CHECKING:
    from erk.core.context import ErkContext
    from erk.core.repo_discovery import RepoContext


@dataclass(frozen=True)
class StackLandEntry:
    """A single entry in a stack to be landed."""

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

    Resolves the stack, validates all PRs, displays a summary, confirms
    with the user, then iterates bottom-up: rebase, re-parent next entry,
    merge, and optionally create learn PRs.

    Returns normally on success. Raises UserFacingCliError on failure.
    """
    Ensure.graphite_available(ctx)

    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # 1. Resolve stack
    branches_to_land = _resolve_stack(ctx, main_repo_root=main_repo_root)

    # 2. Pre-validate all PRs
    trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)
    entries = _validate_stack_prs(
        ctx,
        main_repo_root=main_repo_root,
        branches=branches_to_land,
        trunk=trunk,
        force=force,
    )

    # 3. Display summary
    _display_stack_summary(entries)

    # 4. Dry-run early exit
    if ctx.dry_run:
        user_output(click.style("[DRY RUN] No changes made", fg="yellow", bold=True))
        return

    # 5. Confirm unless --force
    _confirm_stack_land(ctx, entries=entries, force=force)

    # 6. Land each branch bottom-up with partial failure tracking
    landed: list[StackLandEntry] = []
    total = len(entries)

    for i, entry in enumerate(entries):
        try:
            if i > 0:
                _rebase_and_push(
                    ctx, main_repo_root=main_repo_root, branch=entry.branch, trunk=trunk
                )

            # Re-parent ONLY the next entry (O(N) total, not O(N^2))
            if i + 1 < total:
                _reparent_entry(
                    ctx,
                    main_repo_root=main_repo_root,
                    entry=entries[i + 1],
                    trunk=trunk,
                )

            _merge_and_cleanup_branch(ctx, main_repo_root=main_repo_root, entry=entry)
        except UserFacingCliError:
            _report_partial_failure(
                landed=landed, failed=entry, remaining=entries[i + 1 :], total=total
            )
            raise

        landed.append(entry)
        user_output(
            click.style("\u2713", fg="green")
            + f" Merged PR #{entry.pr_number} [{entry.branch}] ({i + 1}/{total})"
        )

        # Learn PR (fire-and-forget, per branch)
        if not skip_learn and entry.plan_id is not None:
            _try_create_learn_pr(ctx, main_repo_root=main_repo_root, entry=entry)

    # 7. Cleanup local branches/worktrees
    if not no_delete:
        _cleanup_after_stack_land(ctx, repo=repo, entries=entries, main_repo_root=main_repo_root)

    # 8. Pull trunk
    if pull_flag:
        _pull_trunk(ctx, main_repo_root=main_repo_root, trunk=trunk)

    # 9. Objective updates (fail-open)
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
        click.style("\u2713", fg="green", bold=True)
        + f" Stack landed: {total} PR(s) merged successfully"
    )


def _resolve_stack(ctx: ErkContext, *, main_repo_root: Path) -> list[str]:
    """Get stack branches excluding trunk, bottom-up order."""
    current_branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(main_repo_root),
        "Not on a branch (detached HEAD). Check out a stack branch first.",
    )

    stack = ctx.graphite.get_branch_stack(ctx.git, main_repo_root, current_branch)
    Ensure.invariant(
        stack is not None and len(stack) > 0,
        f"Branch '{current_branch}' is not part of a Graphite stack.\n"
        "Use 'gt track' to add it to a stack first.",
    )
    assert stack is not None

    # Stack includes trunk as first element — exclude it
    trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)
    branches = [b for b in stack if b != trunk]

    Ensure.invariant(
        len(branches) > 0,
        "Stack contains only the trunk branch. Nothing to land.",
    )

    return branches


def _validate_stack_prs(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    branches: list[str],
    trunk: str,
    force: bool,
) -> list[StackLandEntry]:
    """Pre-validate all PRs in the stack are open and landable."""
    entries: list[StackLandEntry] = []

    for branch in branches:
        pr_result = ctx.github.get_pr_for_branch(main_repo_root, branch)
        if isinstance(pr_result, PRDetails):
            pr_details = pr_result
        else:
            Ensure.invariant(
                False,
                f"No pull request found for branch '{branch}'.\n"
                "All branches in the stack must have open PRs.",
            )
            # Unreachable, but satisfies type checker
            continue

        Ensure.invariant(
            pr_details.state == "OPEN",
            f"PR #{pr_details.number} for branch '{branch}' is not open "
            f"(state: {pr_details.state}).\n"
            "All PRs in the stack must be open to land.",
        )

        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(main_repo_root, branch)
        objective_number = get_objective_for_branch(ctx, main_repo_root, branch)
        worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)

        entries.append(
            StackLandEntry(
                branch=branch,
                pr_number=pr_details.number,
                pr_details=pr_details,
                worktree_path=worktree_path,
                plan_id=plan_id,
                objective_number=objective_number,
            )
        )

    return entries


def _display_stack_summary(entries: list[StackLandEntry]) -> None:
    """Show numbered list of PRs to be landed."""
    user_output("\nStack to land (bottom-up):")
    for i, entry in enumerate(entries, 1):
        user_output(f"  {i}. PR #{entry.pr_number} [{entry.branch}] - {entry.pr_details.title}")
    user_output("")


def _confirm_stack_land(
    ctx: ErkContext,
    *,
    entries: list[StackLandEntry],
    force: bool,
) -> None:
    """Prompt user for confirmation. Raise SystemExit(0) on decline."""
    if force:
        return

    if not ctx.console.confirm(f"Land {len(entries)} PR(s) in this stack?", default=True):
        raise SystemExit(0)


def _rebase_and_push(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    branch: str,
    trunk: str,
) -> None:
    """Fetch trunk, rebase branch onto it, and force-push."""
    ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk)

    # Find the worktree for this branch (rebase needs cwd in the worktree)
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)
    rebase_cwd = worktree_path if worktree_path is not None else main_repo_root

    result = ctx.git.rebase.rebase_onto(rebase_cwd, f"origin/{trunk}")
    if not result.success:
        ctx.git.rebase.rebase_abort(rebase_cwd)
        raise UserFacingCliError(
            f"Rebase conflict on branch '{branch}'.\n"
            f"Conflicting files: {', '.join(result.conflict_files)}\n"
            "Resolve conflicts manually, then retry."
        )

    ctx.git.remote.push_to_remote(rebase_cwd, "origin", branch, set_upstream=False, force=True)


def _reparent_entry(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    entry: StackLandEntry,
    trunk: str,
) -> None:
    """Re-parent a single entry's PR base branch to trunk."""
    ctx.github.update_pr_base_branch(main_repo_root, entry.pr_number, trunk)


def _merge_and_cleanup_branch(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    entry: StackLandEntry,
) -> None:
    """Squash-merge PR and delete the remote branch."""
    result = ctx.github.merge_pr(main_repo_root, entry.pr_number, squash=True, verbose=False)
    if isinstance(result, MergeError):
        raise UserFacingCliError(
            f"Failed to merge PR #{entry.pr_number} [{entry.branch}]: {result.message}"
        )

    ctx.github.delete_remote_branch(main_repo_root, entry.branch)


def _try_create_learn_pr(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    entry: StackLandEntry,
) -> None:
    """Fire-and-forget learn PR creation for a landed entry."""
    if entry.plan_id is None:
        return
    try:
        _create_learn_pr_core(
            ctx,
            repo_root=main_repo_root,
            plan_id=entry.plan_id,
            merged_pr_number=entry.pr_number,
            cwd=main_repo_root,
        )
    except Exception:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Learn plan creation failed for PR #{entry.pr_number}"
        )


def _report_partial_failure(
    *,
    landed: list[StackLandEntry],
    failed: StackLandEntry,
    remaining: list[StackLandEntry],
    total: int,
) -> None:
    """Display partial failure progress report."""
    lines: list[str] = []
    for prev in landed:
        lines.append(click.style("  \u2713 ", fg="green") + f"PR #{prev.pr_number} [{prev.branch}]")
    lines.append(click.style("  \u2717 ", fg="red") + f"PR #{failed.pr_number} [{failed.branch}]")
    for rem in remaining:
        lines.append(click.style("  - ", dim=True) + f"PR #{rem.pr_number} [{rem.branch}]")
    user_output(f"\nStack progress ({len(landed)}/{total} landed):\n" + "\n".join(lines))


def _cleanup_after_stack_land(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    entries: list[StackLandEntry],
    main_repo_root: Path,
) -> None:
    """Delete local branches and worktrees for landed stack entries."""
    for entry in entries:
        # Delete local branch if it exists
        local_branches = ctx.git.branch.list_local_branches(main_repo_root)
        if entry.branch in local_branches:
            # Ensure branch is not checked out before deleting
            wt_for_branch = ctx.git.worktree.find_worktree_for_branch(main_repo_root, entry.branch)
            if wt_for_branch is not None:
                trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)
                ctx.branch_manager.checkout_detached(wt_for_branch, trunk)

            ctx.branch_manager.delete_branch(main_repo_root, entry.branch, force=True)


def _pull_trunk(ctx: ErkContext, *, main_repo_root: Path, trunk: str) -> None:
    """Pull latest trunk after landing."""
    ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk)
    try:
        ctx.git.remote.pull_branch(main_repo_root, "origin", trunk, ff_only=True)
    except RuntimeError:
        user_output(
            click.style("Warning: ", fg="yellow")
            + "git pull failed after landing (try running manually)"
        )
