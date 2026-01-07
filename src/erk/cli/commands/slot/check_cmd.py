"""Slot check command - check pool state consistency with disk and git."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click
from rich.console import Console
from rich.table import Table

from erk.cli.commands.slot.common import generate_slot_name
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
    state: PoolState,
    fs_slots: set[str],
) -> list[SyncIssue]:
    """Check for directories that exist on filesystem but not in pool state.

    Args:
        state: Pool state (to check against known slots)
        fs_slots: Set of slot names found on filesystem

    Returns:
        List of (issue_type, message) tuples
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
    state: PoolState,
    git_slots: dict[str, WorktreeInfo],
) -> list[SyncIssue]:
    """Check for mismatches between pool state and git worktree registry.

    Args:
        state: Pool state (assignments and known slots)
        git_slots: Dict of slot names to WorktreeInfo from git

    Returns:
        List of (issue_type, message) tuples
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


@dataclass(frozen=True)
class SlotCheckResult:
    """Result of checking a single slot."""

    slot_name: str
    assigned_branch: str | None
    issues: tuple[SyncIssue, ...]


# Human-readable descriptions for issue codes
_ISSUE_DESCRIPTIONS: dict[SyncIssueCode, str] = {
    "orphan-state": "dir missing",
    "orphan-dir": "not in pool",
    "missing-branch": "branch deleted",
    "branch-mismatch": "branch mismatch",
    "git-registry-missing": "not in git registry",
    "untracked-worktree": "untracked",
}


def _extract_slot_name_from_issue(issue: SyncIssue) -> str | None:
    """Extract slot name from issue message.

    Returns None if slot name cannot be extracted.
    """
    # Issue messages follow patterns like:
    # "Slot erk-managed-wt-01: ..."
    # "Directory erk-managed-wt-05: ..."
    msg = issue.message
    if msg.startswith("Slot "):
        return msg.split(":")[0].replace("Slot ", "")
    if msg.startswith("Directory "):
        return msg.split(":")[0].replace("Directory ", "")
    return None


def _build_slot_results(
    *,
    state: PoolState,
    all_issues: list[SyncIssue],
) -> tuple[SlotCheckResult, ...]:
    """Build per-slot check results.

    Args:
        state: Pool state
        all_issues: All issues found by diagnostics

    Returns:
        Tuple of SlotCheckResult for each slot in the pool
    """
    # Build lookup of slot_name -> assigned_branch
    assignments_by_slot: dict[str, str] = {
        a.slot_name: a.branch_name for a in state.assignments
    }

    # Group issues by slot name
    issues_by_slot: dict[str, list[SyncIssue]] = {}
    for issue in all_issues:
        slot_name = _extract_slot_name_from_issue(issue)
        if slot_name is not None:
            if slot_name not in issues_by_slot:
                issues_by_slot[slot_name] = []
            issues_by_slot[slot_name].append(issue)

    # Build results for all slots
    results: list[SlotCheckResult] = []
    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        assigned_branch = assignments_by_slot.get(slot_name)
        slot_issues = tuple(issues_by_slot.get(slot_name, []))
        results.append(
            SlotCheckResult(
                slot_name=slot_name,
                assigned_branch=assigned_branch,
                issues=slot_issues,
            )
        )

    return tuple(results)


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
    issues.extend(_check_orphan_dirs(state, fs_slots))
    issues.extend(_check_missing_branches(state.assignments, ctx, repo.root))
    issues.extend(_check_git_worktree_mismatch(state, git_slots))

    return issues


@click.command("check")
@click.pass_obj
def slot_check(ctx: ErkContext) -> None:
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
        user_output("Error: No pool configured. Run `erk slot create` first.")
        raise SystemExit(1) from None

    # Run all diagnostics
    issues = run_sync_diagnostics(ctx, state, repo.root)

    # Build per-slot results
    slot_results = _build_slot_results(state=state, all_issues=issues)

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slot", style="cyan", no_wrap=True)
    table.add_column("Branch", style="yellow", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Issues", no_wrap=True)

    # Track counts for summary
    ok_count = 0
    error_count = 0

    # Add rows for all slots
    for result in slot_results:
        # Format branch display
        branch_display: str
        if result.assigned_branch is not None:
            branch_display = result.assigned_branch
        else:
            branch_display = "[dim]-[/dim]"

        # Format status and issues
        if result.issues:
            status_display = "[red]error[/red]"
            # Build comma-separated issue descriptions
            issue_descriptions = [
                _ISSUE_DESCRIPTIONS[issue.code] for issue in result.issues
            ]
            issues_display = f"[red]{', '.join(issue_descriptions)}[/red]"
            error_count += 1
        else:
            status_display = "[green]ok[/green]"
            issues_display = "[dim]-[/dim]"
            ok_count += 1

        table.add_row(
            result.slot_name,
            branch_display,
            status_display,
            issues_display,
        )

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)

    # Print summary
    console.print(f"\nPool: {state.pool_size} slots | {ok_count} ok | {error_count} errors")
