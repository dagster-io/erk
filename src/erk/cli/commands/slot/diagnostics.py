"""Slot diagnostics - check pool state consistency with disk and git."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from erk.cli.commands.slot.common import generate_slot_name
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment
from erk_shared.git.abc import Git, WorktreeInfo

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
        List of SyncIssue instances
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
    state: PoolState,
    fs_slots: set[str],
) -> list[SyncIssue]:
    """Check for directories that exist on filesystem but not in pool state.

    Args:
        state: Pool state (to check against known slots)
        fs_slots: Set of slot names found on filesystem

    Returns:
        List of SyncIssue instances
    """
    # Generate known slots from pool_size (same logic as slot list command)
    known_slots = {generate_slot_name(i) for i in range(1, state.pool_size + 1)}

    issues: list[SyncIssue] = []
    for slot_name in fs_slots:
        if slot_name not in known_slots:
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
        List of SyncIssue instances
    """
    issues: list[SyncIssue] = []
    for assignment in assignments:
        # Check if branch exists by getting its head commit
        if ctx.git.get_branch_head(repo_root, assignment.branch_name) is None:
            msg = f"Slot {assignment.slot_name}: branch '{assignment.branch_name}' deleted"
            issues.append(SyncIssue(code="missing-branch", message=msg))
    return issues


def _check_git_worktree_mismatch(
    state: PoolState,
    git_slots: dict[str, WorktreeInfo],
) -> list[SyncIssue]:
    """Check for mismatches between pool state and git worktree registry.

    Args:
        state: Pool state (assignments and known slots)
        git_slots: Dict of slot names to WorktreeInfo from git

    Returns:
        List of SyncIssue instances
    """
    issues: list[SyncIssue] = []

    # Check assignments against git registry
    for assignment in state.assignments:
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
    # Generate known slots from pool_size (same logic as slot list command)
    known_slots = {generate_slot_name(i) for i in range(1, state.pool_size + 1)}
    for slot_name, wt in git_slots.items():
        if slot_name not in known_slots:
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
        List of SyncIssue instances
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
    issues.extend(_check_orphan_dirs(state, fs_slots))
    issues.extend(_check_missing_branches(state.assignments, ctx, repo.root))
    issues.extend(_check_git_worktree_mismatch(state, git_slots))

    return issues
