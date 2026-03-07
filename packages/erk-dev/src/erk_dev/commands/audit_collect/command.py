"""Collect and categorize branch/worktree/PR data for audit-branches.

Usage:
    erk-dev audit-collect

Output:
    JSON with pre-categorized branches ready for presentation.

Exit Codes:
    0: Always (outputs JSON with success field)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk_dev.context import ErkDevContext

if TYPE_CHECKING:
    from erk_shared.gateway.git.abc import BranchSyncInfo, WorktreeInfo
    from erk_shared.gateway.github.types import PullRequestInfo


# -- Data types ----------------------------------------------------------------


@dataclass(frozen=True)
class BlockingWorktree:
    """A worktree with a closed/merged PR that blocks automated cleanup."""

    worktree_path: str
    slot_name: str
    is_slot: bool
    branch: str
    pr_number: int
    pr_state: str


@dataclass(frozen=True)
class AutoCleanupBranch:
    """A branch safe to delete with no unique work."""

    branch: str
    reason: str
    ahead_of_master: int
    has_remote: bool


@dataclass(frozen=True)
class ClosedPRBranch:
    """A branch with a closed/merged PR."""

    branch: str
    pr_number: int
    pr_state: str
    in_worktree: bool
    tracked_by_graphite: bool


@dataclass(frozen=True)
class PatternBranchGroup:
    """A group of branches matching a naming pattern."""

    count: int
    branches: list[str]
    parent_pr_states: dict[str, int]


@dataclass(frozen=True)
class StaleOpenPR:
    """An open PR that appears stale or superseded."""

    pr_number: int
    title: str
    reason: str
    details: str
    mergeable: str


@dataclass(frozen=True)
class NeedsAttentionPR:
    """An open PR that needs manual attention."""

    pr_number: int
    title: str
    mergeable: str
    updated_at: str
    branch: str


@dataclass(frozen=True)
class ActivePRs:
    """Summary of active open PRs (not individually listed)."""

    count: int
    note: str


@dataclass(frozen=True)
class AuditCategories:
    """All categorized audit results."""

    blocking_worktrees: list[BlockingWorktree] = field(default_factory=list)
    auto_cleanup: list[AutoCleanupBranch] = field(default_factory=list)
    closed_pr_branches: list[ClosedPRBranch] = field(default_factory=list)
    pattern_branches: dict[str, PatternBranchGroup] = field(default_factory=dict)
    stale_open_prs: list[StaleOpenPR] = field(default_factory=list)
    needs_attention: list[NeedsAttentionPR] = field(default_factory=list)
    active: ActivePRs = field(default_factory=lambda: ActivePRs(count=0, note=""))


@dataclass(frozen=True)
class AuditSummary:
    """High-level counts for the audit."""

    total_local_branches: int
    total_worktrees: int
    total_open_prs: int


@dataclass(frozen=True)
class AuditResult:
    """Top-level audit-collect output."""

    success: bool
    summary: AuditSummary
    categories: AuditCategories
    stubs_tracked_by_graphite: list[str] = field(default_factory=list)


# -- Constants -----------------------------------------------------------------

_STUB_PREFIX = "__erk-slot-"
_STUB_SUFFIX = "-br-stub__"
_ASYNC_LEARN_PREFIX = "async-learn/"

# -- Helpers -------------------------------------------------------------------


def _is_stub_branch(branch: str) -> bool:
    """Check if branch is an erk slot stub placeholder."""
    return branch.startswith(_STUB_PREFIX) and branch.endswith(_STUB_SUFFIX)


def _is_async_learn_branch(branch: str) -> bool:
    """Check if branch follows the async-learn/* pattern."""
    return branch.startswith(_ASYNC_LEARN_PREFIX)


def _parse_pr_number_from_async_learn(branch: str) -> int | None:
    """Extract PR number from async-learn/<number> branch name."""
    suffix = branch.removeprefix(_ASYNC_LEARN_PREFIX)
    if suffix.isdigit():
        return int(suffix)
    return None


def _build_branch_to_worktree_map(
    worktrees: list[WorktreeInfo],
) -> dict[str, WorktreeInfo]:
    """Build mapping from branch name to worktree info."""
    result: dict[str, WorktreeInfo] = {}
    for wt in worktrees:
        if wt.branch is not None:
            result[wt.branch] = wt
    return result


def _is_slot_worktree(worktree_path: str) -> bool:
    """Check if worktree path is an erk slot directory."""
    name = Path(worktree_path).name
    return name.startswith("erk-slot-")


def _get_slot_name(worktree_path: str) -> str:
    """Extract slot name from worktree path."""
    return Path(worktree_path).name


def _collect_blocking_worktrees(
    worktrees: list[WorktreeInfo],
    pr_by_branch: dict[str, PullRequestInfo],
) -> list[BlockingWorktree]:
    """Find worktrees with closed/merged PRs that block gt repo sync."""
    results: list[BlockingWorktree] = []
    for wt in worktrees:
        if wt.branch is None or wt.is_root:
            continue
        if _is_stub_branch(wt.branch):
            continue
        if wt.branch not in pr_by_branch:
            continue
        pr = pr_by_branch[wt.branch]
        if pr.state in ("CLOSED", "MERGED"):
            wt_path = str(wt.path)
            results.append(
                BlockingWorktree(
                    worktree_path=wt_path,
                    slot_name=_get_slot_name(wt_path),
                    is_slot=_is_slot_worktree(wt_path),
                    branch=wt.branch,
                    pr_number=pr.number,
                    pr_state=pr.state,
                )
            )
    return results


def _collect_auto_cleanup(
    local_branches: list[str],
    remote_branch_set: set[str],
    sync_info: dict[str, BranchSyncInfo],
    branch_to_wt: dict[str, WorktreeInfo],
    pr_by_branch: dict[str, PullRequestInfo],
    trunk: str,
) -> list[AutoCleanupBranch]:
    """Find branches safe to delete (0 ahead of master, no unique work)."""
    results: list[AutoCleanupBranch] = []
    for branch in local_branches:
        if branch == trunk:
            continue
        if _is_stub_branch(branch):
            continue
        if _is_async_learn_branch(branch):
            continue
        # Skip branches with open PRs
        if branch in pr_by_branch and pr_by_branch[branch].state == "OPEN":
            continue
        # Skip branches in worktrees (handled by blocking_worktrees)
        if branch in branch_to_wt:
            continue

        has_remote = f"origin/{branch}" in remote_branch_set
        info = sync_info.get(branch)

        # Branch with no tracking info and no remote — local-only
        if info is None and not has_remote:
            results.append(
                AutoCleanupBranch(
                    branch=branch,
                    reason="local_only_no_tracking",
                    ahead_of_master=0,
                    has_remote=False,
                )
            )
            continue

        # Branch with sync info showing 0 ahead
        if info is not None and info.ahead == 0:
            reason = "merged_to_trunk" if info.gone else "zero_ahead"
            results.append(
                AutoCleanupBranch(
                    branch=branch,
                    reason=reason,
                    ahead_of_master=0,
                    has_remote=has_remote,
                )
            )
    return results


def _collect_closed_pr_branches(
    local_branches: list[str],
    pr_by_branch: dict[str, PullRequestInfo],
    branch_to_wt: dict[str, WorktreeInfo],
    graphite_branches: set[str],
    auto_cleanup_branches: set[str],
) -> list[ClosedPRBranch]:
    """Find branches with closed/merged PRs not in worktrees."""
    results: list[ClosedPRBranch] = []
    for branch in local_branches:
        if _is_stub_branch(branch):
            continue
        if branch in auto_cleanup_branches:
            continue
        if branch not in pr_by_branch:
            continue
        pr = pr_by_branch[branch]
        if pr.state not in ("CLOSED", "MERGED"):
            continue
        results.append(
            ClosedPRBranch(
                branch=branch,
                pr_number=pr.number,
                pr_state=pr.state,
                in_worktree=branch in branch_to_wt,
                tracked_by_graphite=branch in graphite_branches,
            )
        )
    return results


def _collect_pattern_branches(
    local_branches: list[str],
    pr_by_branch: dict[str, PullRequestInfo],
) -> dict[str, PatternBranchGroup]:
    """Collect branches matching known naming patterns."""
    groups: dict[str, PatternBranchGroup] = {}

    # async-learn/* pattern
    async_learn_branches: list[str] = []
    state_counts: dict[str, int] = {}
    for branch in local_branches:
        if not _is_async_learn_branch(branch):
            continue
        async_learn_branches.append(branch)
        pr_number = _parse_pr_number_from_async_learn(branch)
        if pr_number is not None and branch in pr_by_branch:
            state = pr_by_branch[branch].state
            state_counts[state] = state_counts.get(state, 0) + 1

    if async_learn_branches:
        groups["async_learn"] = PatternBranchGroup(
            count=len(async_learn_branches),
            branches=sorted(async_learn_branches),
            parent_pr_states=state_counts,
        )

    return groups


def _collect_stale_and_attention_prs(
    pr_by_branch: dict[str, PullRequestInfo],
    now: datetime,
) -> tuple[list[StaleOpenPR], list[NeedsAttentionPR], int]:
    """Categorize open PRs into stale, needs-attention, and active counts.

    Returns:
        Tuple of (stale_prs, needs_attention_prs, active_count)
    """
    stale: list[StaleOpenPR] = []
    needs_attention: list[NeedsAttentionPR] = []
    active_count = 0

    for branch, pr in pr_by_branch.items():
        if pr.state != "OPEN":
            continue

        mergeable = "UNKNOWN"
        if pr.has_conflicts:
            mergeable = "CONFLICTING"
        elif pr.has_conflicts is False:
            mergeable = "MERGEABLE"

        # PRs with conflicts are flagged as needs-attention
        if mergeable == "CONFLICTING":
            needs_attention.append(
                NeedsAttentionPR(
                    pr_number=pr.number,
                    title=pr.title or "",
                    mergeable=mergeable,
                    updated_at="",
                    branch=branch,
                )
            )
        else:
            active_count += 1

    return stale, needs_attention, active_count


# -- Main command --------------------------------------------------------------


def _run_audit_collect(
    repo_root: Path,
    *,
    local_branches: list[str],
    remote_branches: list[str],
    worktrees: list[WorktreeInfo],
    sync_info: dict[str, BranchSyncInfo],
    pr_by_branch: dict[str, PullRequestInfo],
    trunk: str,
    now: datetime,
    graphite_branches: set[str],
) -> AuditResult:
    """Core audit collection logic, separated for testability.

    All data is pre-fetched and passed in; this function only categorizes.
    """
    remote_branch_set = set(remote_branches)
    branch_to_wt = _build_branch_to_worktree_map(worktrees)

    # Categorize
    blocking = _collect_blocking_worktrees(worktrees, pr_by_branch)
    auto_cleanup = _collect_auto_cleanup(
        local_branches, remote_branch_set, sync_info, branch_to_wt, pr_by_branch, trunk
    )
    auto_cleanup_set = {b.branch for b in auto_cleanup}

    closed_pr = _collect_closed_pr_branches(
        local_branches, pr_by_branch, branch_to_wt, graphite_branches, auto_cleanup_set
    )
    patterns = _collect_pattern_branches(local_branches, pr_by_branch)

    stale, attention, active_count = _collect_stale_and_attention_prs(pr_by_branch, now)

    # Detect stubs tracked by Graphite
    stubs_tracked = [b for b in graphite_branches if _is_stub_branch(b)]

    # Count open PRs
    open_pr_count = sum(1 for pr in pr_by_branch.values() if pr.state == "OPEN")

    return AuditResult(
        success=True,
        summary=AuditSummary(
            total_local_branches=len(local_branches),
            total_worktrees=len(worktrees),
            total_open_prs=open_pr_count,
        ),
        categories=AuditCategories(
            blocking_worktrees=blocking,
            auto_cleanup=auto_cleanup,
            closed_pr_branches=closed_pr,
            pattern_branches=patterns,
            stale_open_prs=stale,
            needs_attention=attention,
            active=ActivePRs(
                count=active_count,
                note="Recent open PRs with active work, skipped",
            ),
        ),
        stubs_tracked_by_graphite=sorted(stubs_tracked),
    )


@click.command(name="audit-collect")
@click.pass_context
def audit_collect_command(ctx: click.Context) -> None:
    """Collect and categorize branch/worktree/PR data for audit.

    Outputs comprehensive JSON with pre-categorized branches for
    the audit-branches slash command to present.
    """
    dev_ctx: ErkDevContext = ctx.obj
    git = dev_ctx.git
    github = dev_ctx.github
    repo_root = dev_ctx.repo_root

    # Fetch all data
    local_branches = git.branch.list_local_branches(repo_root)
    remote_branches = git.branch.list_remote_branches(repo_root)
    worktrees = git.worktree.list_worktrees(repo_root)
    trunk = git.branch.detect_trunk_branch(repo_root)
    sync_info = git.branch.get_all_branch_sync_info(repo_root)

    # Fetch all PRs (open + closed) in one call
    all_prs = github.list_prs(repo_root, state="all")

    # Graphite tracking detection — use subprocess since no gateway exists
    graphite_branches: set[str] = set()
    try:
        import subprocess

        result = subprocess.run(
            ["gt", "log", "short", "--no-interactive"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                stripped = line.strip()
                # gt log short outputs branch names with optional markers
                # Strip leading symbols like ◉, ○, │, etc.
                for char in ("◉", "○", "│", "─", "├", "└", "●", "◯", "*", " "):
                    stripped = stripped.lstrip(char)
                stripped = stripped.strip()
                if stripped:
                    graphite_branches.add(stripped)
    except FileNotFoundError:
        pass  # gt not installed

    now = datetime.now(tz=UTC)

    audit_result = _run_audit_collect(
        repo_root,
        local_branches=local_branches,
        remote_branches=remote_branches,
        worktrees=worktrees,
        sync_info=sync_info,
        pr_by_branch=all_prs,
        trunk=trunk,
        now=now,
        graphite_branches=graphite_branches,
    )

    click.echo(json.dumps(asdict(audit_result), indent=2))
    raise SystemExit(0)
