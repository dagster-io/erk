"""Unit tests for audit-collect erk-dev command.

Tests the branch/worktree/PR categorization logic using pure function tests
and CLI integration tests with fakes.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk_dev.cli import cli
from erk_dev.commands.audit_collect.command import (
    _is_async_learn_branch,
    _is_stub_branch,
    _run_audit_collect,
)
from erk_dev.context import ErkDevContext
from erk_shared.gateway.git.abc import BranchSyncInfo, WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PullRequestInfo

_REPO = Path("/fake/repo")
_NOW = datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC)


def _make_pr(
    number: int,
    state: str,
    *,
    branch: str | None = None,
    has_conflicts: bool | None = None,
    title: str | None = None,
) -> PullRequestInfo:
    """Create a PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/test/repo/pull/{number}",
        is_draft=False,
        title=title or f"PR #{number}",
        checks_passing=None,
        owner="test",
        repo="repo",
        has_conflicts=has_conflicts,
        head_branch=branch,
    )


# ============================================================================
# 1. Helper function tests
# ============================================================================


def test_is_stub_branch() -> None:
    """Stub branches are correctly identified."""
    assert _is_stub_branch("__erk-slot-03-br-stub__") is True
    assert _is_stub_branch("__erk-slot-99-br-stub__") is True
    assert _is_stub_branch("plnd/my-feature") is False
    assert _is_stub_branch("master") is False


def test_is_async_learn_branch() -> None:
    """Async-learn branches are correctly identified."""
    assert _is_async_learn_branch("async-learn/8646") is True
    assert _is_async_learn_branch("async-learn/abc") is True
    assert _is_async_learn_branch("plnd/async-learn") is False
    assert _is_async_learn_branch("master") is False


# ============================================================================
# 2. Core logic tests (_run_audit_collect)
# ============================================================================


def test_empty_repo() -> None:
    """Empty repo with only master produces empty categories."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master"],
        remote_branches=["origin/master"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert result.success is True
    assert result.summary.total_local_branches == 1
    assert result.summary.total_worktrees == 1
    assert result.summary.total_open_prs == 0
    assert len(result.categories.blocking_worktrees) == 0
    assert len(result.categories.auto_cleanup) == 0
    assert len(result.categories.closed_pr_branches) == 0


def test_blocking_worktree_detection() -> None:
    """Worktree with closed PR is flagged as blocking."""
    slot_path = Path("/slots/erk-slot-03")
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "plnd/old-feature"],
        remote_branches=["origin/master", "origin/plnd/old-feature"],
        worktrees=[
            WorktreeInfo(path=_REPO, branch="master", is_root=True),
            WorktreeInfo(path=slot_path, branch="plnd/old-feature"),
        ],
        sync_info={},
        pr_by_branch={"plnd/old-feature": _make_pr(100, "CLOSED")},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.blocking_worktrees) == 1
    blocking = result.categories.blocking_worktrees[0]
    assert blocking.branch == "plnd/old-feature"
    assert blocking.pr_number == 100
    assert blocking.pr_state == "CLOSED"
    assert blocking.is_slot is True
    assert blocking.slot_name == "erk-slot-03"


def test_blocking_worktree_merged_pr() -> None:
    """Worktree with merged PR is also flagged as blocking."""
    wt_path = Path("/worktrees/my-feature")
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "my-feature"],
        remote_branches=["origin/master"],
        worktrees=[
            WorktreeInfo(path=_REPO, branch="master", is_root=True),
            WorktreeInfo(path=wt_path, branch="my-feature"),
        ],
        sync_info={},
        pr_by_branch={"my-feature": _make_pr(200, "MERGED")},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.blocking_worktrees) == 1
    blocking = result.categories.blocking_worktrees[0]
    assert blocking.pr_state == "MERGED"
    assert blocking.is_slot is False


def test_stub_branches_excluded_from_blocking() -> None:
    """Stub branches in worktrees are NOT flagged as blocking."""
    slot_path = Path("/slots/erk-slot-05")
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "__erk-slot-05-br-stub__"],
        remote_branches=["origin/master"],
        worktrees=[
            WorktreeInfo(path=_REPO, branch="master", is_root=True),
            WorktreeInfo(path=slot_path, branch="__erk-slot-05-br-stub__"),
        ],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.blocking_worktrees) == 0


def test_auto_cleanup_zero_ahead() -> None:
    """Branch with 0 commits ahead is flagged for auto-cleanup."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "stale-branch"],
        remote_branches=["origin/master", "origin/stale-branch"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={
            "stale-branch": BranchSyncInfo(
                branch="stale-branch", upstream="origin/stale-branch", ahead=0, behind=3
            ),
        },
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.auto_cleanup) == 1
    cleanup = result.categories.auto_cleanup[0]
    assert cleanup.branch == "stale-branch"
    assert cleanup.reason == "zero_ahead"
    assert cleanup.has_remote is True


def test_auto_cleanup_local_only_no_tracking() -> None:
    """Local-only branch with no tracking info is flagged for auto-cleanup."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "orphan-local"],
        remote_branches=["origin/master"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.auto_cleanup) == 1
    cleanup = result.categories.auto_cleanup[0]
    assert cleanup.branch == "orphan-local"
    assert cleanup.reason == "local_only_no_tracking"
    assert cleanup.has_remote is False


def test_auto_cleanup_gone_upstream() -> None:
    """Branch with gone upstream is flagged as merged_to_trunk."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "gone-branch"],
        remote_branches=["origin/master"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={
            "gone-branch": BranchSyncInfo(
                branch="gone-branch", upstream="origin/gone-branch", ahead=0, behind=0, gone=True
            ),
        },
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.auto_cleanup) == 1
    assert result.categories.auto_cleanup[0].reason == "merged_to_trunk"


def test_auto_cleanup_skips_open_pr_branches() -> None:
    """Branches with open PRs are not flagged for auto-cleanup."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "active-feature"],
        remote_branches=["origin/master", "origin/active-feature"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={
            "active-feature": BranchSyncInfo(
                branch="active-feature",
                upstream="origin/active-feature",
                ahead=0,
                behind=0,
            ),
        },
        pr_by_branch={"active-feature": _make_pr(300, "OPEN")},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.auto_cleanup) == 0


def test_auto_cleanup_skips_worktree_branches() -> None:
    """Branches checked out in worktrees are not auto-cleaned."""
    wt_path = Path("/slots/erk-slot-01")
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "in-worktree"],
        remote_branches=["origin/master"],
        worktrees=[
            WorktreeInfo(path=_REPO, branch="master", is_root=True),
            WorktreeInfo(path=wt_path, branch="in-worktree"),
        ],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.auto_cleanup) == 0


def test_closed_pr_branches() -> None:
    """Branches with closed PRs are categorized correctly."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "closed-feature", "merged-feature"],
        remote_branches=["origin/master", "origin/closed-feature", "origin/merged-feature"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={
            "closed-feature": BranchSyncInfo(
                branch="closed-feature", upstream="origin/closed-feature", ahead=3, behind=0
            ),
            "merged-feature": BranchSyncInfo(
                branch="merged-feature", upstream="origin/merged-feature", ahead=2, behind=0
            ),
        },
        pr_by_branch={
            "closed-feature": _make_pr(400, "CLOSED"),
            "merged-feature": _make_pr(401, "MERGED"),
        },
        trunk="master",
        now=_NOW,
        graphite_branches={"closed-feature"},
    )

    assert len(result.categories.closed_pr_branches) == 2
    branches_by_name = {b.branch: b for b in result.categories.closed_pr_branches}

    assert branches_by_name["closed-feature"].pr_state == "CLOSED"
    assert branches_by_name["closed-feature"].tracked_by_graphite is True
    assert branches_by_name["merged-feature"].pr_state == "MERGED"
    assert branches_by_name["merged-feature"].tracked_by_graphite is False


def test_closed_pr_branches_exclude_auto_cleanup() -> None:
    """Branches already in auto-cleanup are not duplicated in closed_pr_branches."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "merged-zero-ahead"],
        remote_branches=["origin/master", "origin/merged-zero-ahead"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={
            "merged-zero-ahead": BranchSyncInfo(
                branch="merged-zero-ahead",
                upstream="origin/merged-zero-ahead",
                ahead=0,
                behind=0,
            ),
        },
        pr_by_branch={"merged-zero-ahead": _make_pr(500, "MERGED")},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    # Should be in auto_cleanup (0 ahead) but NOT in closed_pr_branches
    assert len(result.categories.auto_cleanup) == 1
    assert result.categories.auto_cleanup[0].branch == "merged-zero-ahead"
    assert len(result.categories.closed_pr_branches) == 0


def test_async_learn_pattern_branches() -> None:
    """async-learn/* branches are grouped as pattern branches."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "async-learn/8646", "async-learn/8700", "async-learn/abc"],
        remote_branches=["origin/master"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert "async_learn" in result.categories.pattern_branches
    group = result.categories.pattern_branches["async_learn"]
    assert group.count == 3
    assert "async-learn/8646" in group.branches
    assert "async-learn/8700" in group.branches
    assert "async-learn/abc" in group.branches


def test_async_learn_not_in_auto_cleanup() -> None:
    """async-learn/* branches are not duplicated in auto-cleanup."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "async-learn/1234"],
        remote_branches=["origin/master"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    # Should be in pattern_branches only
    assert "async_learn" in result.categories.pattern_branches
    auto_branches = [b.branch for b in result.categories.auto_cleanup]
    assert "async-learn/1234" not in auto_branches


def test_needs_attention_conflicting_pr() -> None:
    """Open PRs with conflicts are flagged as needs-attention."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "conflict-branch"],
        remote_branches=["origin/master", "origin/conflict-branch"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={
            "conflict-branch": _make_pr(
                600, "OPEN", has_conflicts=True, title="Conflicting Feature"
            ),
        },
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert len(result.categories.needs_attention) == 1
    pr = result.categories.needs_attention[0]
    assert pr.pr_number == 600
    assert pr.mergeable == "CONFLICTING"
    assert pr.title == "Conflicting Feature"


def test_active_pr_count() -> None:
    """Open PRs without conflicts are counted as active."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "feat-a", "feat-b"],
        remote_branches=["origin/master", "origin/feat-a", "origin/feat-b"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={
            "feat-a": _make_pr(700, "OPEN", has_conflicts=False),
            "feat-b": _make_pr(701, "OPEN", has_conflicts=False),
        },
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert result.categories.active.count == 2


def test_stubs_tracked_by_graphite() -> None:
    """Stub branches tracked by Graphite are detected."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "__erk-slot-03-br-stub__", "__erk-slot-07-br-stub__"],
        remote_branches=["origin/master"],
        worktrees=[WorktreeInfo(path=_REPO, branch="master", is_root=True)],
        sync_info={},
        pr_by_branch={},
        trunk="master",
        now=_NOW,
        graphite_branches={
            "__erk-slot-03-br-stub__",
            "__erk-slot-07-br-stub__",
            "plnd/real-branch",
        },
    )

    assert sorted(result.stubs_tracked_by_graphite) == [
        "__erk-slot-03-br-stub__",
        "__erk-slot-07-br-stub__",
    ]


def test_summary_counts() -> None:
    """Summary counts reflect total branches, worktrees, and open PRs."""
    result = _run_audit_collect(
        _REPO,
        local_branches=["master", "feat-a", "feat-b", "closed-c"],
        remote_branches=["origin/master"],
        worktrees=[
            WorktreeInfo(path=_REPO, branch="master", is_root=True),
            WorktreeInfo(path=Path("/slots/erk-slot-01"), branch="feat-a"),
        ],
        sync_info={},
        pr_by_branch={
            "feat-a": _make_pr(800, "OPEN"),
            "feat-b": _make_pr(801, "OPEN"),
            "closed-c": _make_pr(802, "CLOSED"),
        },
        trunk="master",
        now=_NOW,
        graphite_branches=set(),
    )

    assert result.summary.total_local_branches == 4
    assert result.summary.total_worktrees == 2
    assert result.summary.total_open_prs == 2


# ============================================================================
# 3. CLI integration test
# ============================================================================


def test_cli_produces_valid_json(tmp_path: Path) -> None:
    """CLI command produces valid JSON output with expected structure."""
    runner = CliRunner()

    git = FakeGit(
        local_branches={tmp_path: ["master", "feat-x"]},
        remote_branches={tmp_path: ["origin/master", "origin/feat-x"]},
        worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="master", is_root=True)]},
        trunk_branches={tmp_path: "master"},
        branch_sync_info={
            tmp_path: {
                "feat-x": BranchSyncInfo(
                    branch="feat-x", upstream="origin/feat-x", ahead=1, behind=0
                ),
            }
        },
    )
    github = FakeGitHub(
        prs={
            "feat-x": _make_pr(900, "OPEN", has_conflicts=False),
        },
    )

    ctx = ErkDevContext(git=git, github=github, repo_root=tmp_path)
    result = runner.invoke(cli, ["audit-collect"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "summary" in output
    assert "categories" in output
    assert output["summary"]["total_local_branches"] == 2
    assert output["summary"]["total_open_prs"] == 1


def test_mixed_scenario() -> None:
    """Comprehensive test with mix of all branch types."""
    slot_path = Path("/slots/erk-slot-02")
    result = _run_audit_collect(
        _REPO,
        local_branches=[
            "master",
            "plnd/active-plan",
            "plnd/old-closed",
            "plnd/blocking-in-slot",
            "__erk-slot-02-br-stub__",
            "async-learn/5000",
            "async-learn/5001",
            "orphan-local",
        ],
        remote_branches=[
            "origin/master",
            "origin/plnd/active-plan",
            "origin/plnd/old-closed",
            "origin/plnd/blocking-in-slot",
        ],
        worktrees=[
            WorktreeInfo(path=_REPO, branch="master", is_root=True),
            WorktreeInfo(path=slot_path, branch="plnd/blocking-in-slot"),
        ],
        sync_info={
            "plnd/active-plan": BranchSyncInfo(
                branch="plnd/active-plan",
                upstream="origin/plnd/active-plan",
                ahead=5,
                behind=0,
            ),
            "plnd/old-closed": BranchSyncInfo(
                branch="plnd/old-closed",
                upstream="origin/plnd/old-closed",
                ahead=3,
                behind=10,
            ),
            "plnd/blocking-in-slot": BranchSyncInfo(
                branch="plnd/blocking-in-slot",
                upstream="origin/plnd/blocking-in-slot",
                ahead=2,
                behind=0,
            ),
        },
        pr_by_branch={
            "plnd/active-plan": _make_pr(1000, "OPEN", has_conflicts=False),
            "plnd/old-closed": _make_pr(1001, "CLOSED"),
            "plnd/blocking-in-slot": _make_pr(1002, "CLOSED"),
        },
        trunk="master",
        now=_NOW,
        graphite_branches={"plnd/active-plan", "plnd/old-closed", "__erk-slot-02-br-stub__"},
    )

    assert result.success is True

    # Blocking: slot with closed PR
    assert len(result.categories.blocking_worktrees) == 1
    assert result.categories.blocking_worktrees[0].branch == "plnd/blocking-in-slot"

    # Auto-cleanup: orphan-local (no tracking, no remote)
    auto_branches = {b.branch for b in result.categories.auto_cleanup}
    assert "orphan-local" in auto_branches

    # Closed PR branches: plnd/old-closed (has commits ahead, so not auto-cleanup)
    closed_branches = {b.branch for b in result.categories.closed_pr_branches}
    assert "plnd/old-closed" in closed_branches

    # Pattern branches: async-learn/*
    assert "async_learn" in result.categories.pattern_branches
    assert result.categories.pattern_branches["async_learn"].count == 2

    # Active: plnd/active-plan
    assert result.categories.active.count == 1

    # Stubs tracked by Graphite
    assert "__erk-slot-02-br-stub__" in result.stubs_tracked_by_graphite

    # Summary
    assert result.summary.total_local_branches == 8
    assert result.summary.total_open_prs == 1
