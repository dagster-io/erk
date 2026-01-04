"""Pooled check command - check pool state consistency with disk and git."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk_shared.git.abc import Git, WorktreeInfo
from erk_shared.output.output import user_output

# Type alias for sync issue codes - using Literal for type safety
SyncIssueCode = Literal[
    "orphan-state",
    "orphan-dir",
    "missing-branch",
    "branch-mismatch",
    "git-registry-missing",
    "untracked-worktree",
]


@dataclass(frozen=True)
class SyncIssue:
    """A sync diagnostic issue found during pool state check."""

    code: SyncIssueCode
    message: str


def _find_erk_managed_dirs(worktrees_dir: Path, git: Git) -> set[str]:
    """Find directories in worktrees_dir matching erk-managed-wt-* pattern.

    Args:
        worktrees_dir: Path to the worktrees directory
        git: Git abstraction for path_exists and is_dir checks

    Returns:
        Set of slot names (e.g., {"erk-managed-wt-01", "erk-managed-wt-02"})
    """
    if not git.path_exists(worktrees_dir):
        return set()

    result: set[str] = set()
    # Iterate over worktrees_dir contents
    # Use path_exists to validate before iterdir
    for entry in worktrees_dir.iterdir():
        if entry.name.startswith("erk-managed-wt-") and git.is_dir(entry):
            result.add(entry.name)
    return result


def _get_git_managed_slots(
    worktrees: list[WorktreeInfo], worktrees_dir: Path
) -> dict[str, WorktreeInfo]:
    """Get worktrees that are erk-managed pool slots.

    Args:
        worktrees: List of all git worktrees
        worktrees_dir: Path to the worktrees directory

    Returns:
        Dict mapping slot name to WorktreeInfo for erk-managed slots
    """
    result: dict[str, WorktreeInfo] = {}
    for wt in worktrees:
        if wt.path.parent == worktrees_dir and wt.path.name.startswith("erk-managed-wt-"):
            result[wt.path.name] = wt
    return result


def _check_orphan_states(
    assignments: tuple[SlotAssignment, ...],
    ctx: ErkContext,
) -> list[SyncIssue]:
    """Check for assignments where the worktree directory doesn't exist.

    Args:
        assignments: Current pool assignments
        ctx: Erk context (for git.path_exists)

    Returns:
        List of (issue_type, message) tuples
    """
    issues: list[SyncIssue] = []
    for assignment in assignments:
        if not ctx.git.path_exists(assignment.worktree_path):
            issues.append(
                SyncIssue(
                    code="orphan-state",
                    message=f"Slot {assignment.slot_name}: directory does not exist",
                )
            )
    return issues


def _check_orphan_dirs(
    assignments: tuple[SlotAssignment, ...],
    fs_slots: set[str],
) -> list[SyncIssue]:
    """Check for directories that exist on filesystem but not in pool state.

    Args:
        assignments: Current pool assignments
        fs_slots: Set of slot names found on filesystem

    Returns:
        List of (issue_type, message) tuples
    """
    # Get slots that have assignments
    assigned_slots = {a.slot_name for a in assignments}

    issues: list[SyncIssue] = []
    for slot_name in fs_slots:
        if slot_name not in assigned_slots:
            issues.append(
                SyncIssue(
                    code="orphan-dir",
                    message=f"Directory {slot_name}: not in pool state",
                )
            )
    return issues


def _check_missing_branches(
    assignments: tuple[SlotAssignment, ...],
    ctx: ErkContext,
    repo_root: Path,
) -> list[SyncIssue]:
    """Check for assignments where the branch no longer exists in git.

    Args:
        assignments: Current pool assignments
        ctx: Erk context (for git.get_branch_head)
        repo_root: Path to the repository root

    Returns:
        List of (issue_type, message) tuples
    """
    issues: list[SyncIssue] = []
    for assignment in assignments:
        # Check if branch exists by getting its head commit
        if ctx.git.get_branch_head(repo_root, assignment.branch_name) is None:
            msg = f"Slot {assignment.slot_name}: branch '{assignment.branch_name}' deleted"
            issues.append(SyncIssue(code="missing-branch", message=msg))
    return issues


def _check_git_worktree_mismatch(
    assignments: tuple[SlotAssignment, ...],
    git_slots: dict[str, WorktreeInfo],
) -> list[SyncIssue]:
    """Check for mismatches between pool state and git worktree registry.

    Args:
        assignments: Current pool assignments
        git_slots: Dict of slot names to WorktreeInfo from git

    Returns:
        List of (issue_type, message) tuples
    """
    issues: list[SyncIssue] = []

    # Check assignments against git registry
    for assignment in assignments:
        if assignment.slot_name in git_slots:
            wt = git_slots[assignment.slot_name]
            # Check if branch matches
            if wt.branch != assignment.branch_name:
                msg = (
                    f"Slot {assignment.slot_name}: pool says '{assignment.branch_name}', "
                    f"git says '{wt.branch}'"
                )
                issues.append(SyncIssue(code="branch-mismatch", message=msg))
        else:
            # Slot is in pool.json but not in git worktree registry
            issues.append(
                SyncIssue(
                    code="git-registry-missing",
                    message=f"Slot {assignment.slot_name}: not in git worktree registry",
                )
            )

    # Check git registry for slots not in pool state
    assigned_slots = {a.slot_name for a in assignments}
    for slot_name, wt in git_slots.items():
        if slot_name not in assigned_slots:
            msg = f"Slot {slot_name}: in git registry (branch '{wt.branch}') but not in pool state"
            issues.append(SyncIssue(code="untracked-worktree", message=msg))

    return issues


def run_sync_diagnostics(ctx: ErkContext, state: PoolState, repo_root: Path) -> list[SyncIssue]:
    """Run all sync diagnostics and return issues found.

    Args:
        ctx: Erk context
        state: Pool state to check
        repo_root: Repository root path

    Returns:
        List of (issue_type, message) tuples
    """
    repo = discover_repo_context(ctx, repo_root)

    # Get git worktrees
    worktrees = ctx.git.list_worktrees(repo.root)
    git_slots = _get_git_managed_slots(worktrees, repo.worktrees_dir)

    # Get filesystem state
    fs_slots = _find_erk_managed_dirs(repo.worktrees_dir, ctx.git)

    # Run all checks
    issues: list[SyncIssue] = []
    issues.extend(_check_orphan_states(state.assignments, ctx))
    issues.extend(_check_orphan_dirs(state.assignments, fs_slots))
    issues.extend(_check_missing_branches(state.assignments, ctx, repo.root))
    issues.extend(_check_git_worktree_mismatch(state.assignments, git_slots))

    return issues


@click.command("check")
@click.pass_obj
def pooled_check(ctx: ErkContext) -> None:
    """Check pool state consistency with disk and git.

    Reports drift between:
    - Pool state (pool.json)
    - Filesystem (worktree directories)
    - Git worktree registry

    This is a diagnostic command - it does not modify anything.
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk pooled create` first.")
        raise SystemExit(1) from None

    # Get git worktrees
    worktrees = ctx.git.list_worktrees(repo.root)
    git_slots = _get_git_managed_slots(worktrees, repo.worktrees_dir)

    # Get filesystem state
    fs_slots = _find_erk_managed_dirs(repo.worktrees_dir, ctx.git)

    # Run all checks
    issues: list[SyncIssue] = []
    issues.extend(_check_orphan_states(state.assignments, ctx))
    issues.extend(_check_orphan_dirs(state.assignments, fs_slots))
    issues.extend(_check_missing_branches(state.assignments, ctx, repo.root))
    issues.extend(_check_git_worktree_mismatch(state.assignments, git_slots))

    # Print report
    user_output("Pool Check Report")
    user_output("================")
    user_output("")
    user_output(f"Pool state: {len(state.assignments)} assignments")
    user_output(f"Git worktrees: {len(worktrees)} registered ({len(git_slots)} erk-managed)")
    user_output(f"Filesystem: {len(fs_slots)} slot directories")
    user_output("")

    if issues:
        user_output("Issues Found:")
        for issue in issues:
            user_output(f"  [{issue.code}] {issue.message}")
    else:
        user_output(click.style("✓ No issues found", fg="green"))
