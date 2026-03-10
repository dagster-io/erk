"""Unit tests for wt list command helper functions."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from erk.cli.commands.wt.list_cmd import (
    _format_impl_cell,
    _format_last_commit_cell,
    _format_pr_cell,
    _format_sync_from_batch,
    _get_impl_issue,
    _get_sync_status,
)
from erk_shared.gateway.git.abc import BranchSyncInfo
from erk_shared.gateway.github.types import PullRequestInfo
from tests.fakes.gateway.git import FakeGit
from tests.fakes.tests.context import create_test_context


def test_get_sync_status_current() -> None:
    """Test sync status returns 'current' when branch is up-to-date."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (0, 0)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "current"


def test_get_sync_status_ahead_only() -> None:
    """Test sync status returns 'N↑' when ahead only."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (3, 0)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "3↑"


def test_get_sync_status_behind_only() -> None:
    """Test sync status returns 'N↓' when behind only."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (0, 2)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "2↓"


def test_get_sync_status_ahead_and_behind() -> None:
    """Test sync status returns 'N↑ M↓' when both ahead and behind."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (5, 3)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "5↑ 3↓"


def test_get_sync_status_none_branch() -> None:
    """Test sync status returns '-' when branch is None (detached HEAD)."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit()
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, None)

    assert result == "-"


def test_get_impl_issue_from_impl_folder(tmp_path: Path) -> None:
    """Test getting impl issue from branch-scoped impl folder."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    branch = "feature"
    impl_dir = worktree_path / ".erk" / "impl-context" / branch
    impl_dir.mkdir(parents=True)

    # Create plan.md (required for get_impl_path to return path)
    plan_file = impl_dir / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    # Create ref.json (plan-ref format)
    ref_file = impl_dir / "ref.json"
    ref_file.write_text(
        '{"provider": "github", "plan_id": "42", "url": "https://github.com/owner/repo/issues/42", '
        '"created_at": "2024-01-01T00:00:00Z", "synced_at": "2024-01-01T00:00:00Z"}',
        encoding="utf-8",
    )

    git = FakeGit(existing_paths={plan_file}, current_branches={worktree_path: branch})
    ctx = create_test_context(git=git)

    issue_text, issue_url = _get_impl_issue(ctx, worktree_path, branch=branch)

    assert issue_text == "#42"
    assert issue_url == "https://github.com/owner/repo/issues/42"


def test_get_impl_issue_none_when_not_found() -> None:
    """Test getting impl issue returns (None, None) when no .impl/ folder exists."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit()
    ctx = create_test_context(git=git)

    issue_text, issue_url = _get_impl_issue(ctx, worktree_path, branch="some-branch")

    assert issue_text is None
    assert issue_url is None


def test_format_pr_cell_with_pr_and_graphite_url() -> None:
    """Test formatting PR cell with PR info and Graphite URL."""
    pr = PullRequestInfo(
        number=123,
        state="OPEN",
        is_draft=False,
        url="https://github.com/owner/repo/pull/123",
        owner="owner",
        repo="repo",
        title="Add feature",
        checks_passing=None,
    )

    result = _format_pr_cell(
        pr,
        use_graphite=True,
        graphite_url="https://app.graphite.dev/github/pr/owner/repo/123",
    )

    assert "#123" in result
    assert "👀" in result  # Default open PR emoji
    assert "[link=" in result  # Has Rich link markup
    assert "https://app.graphite.dev/github/pr/owner/repo/123" in result


def test_format_pr_cell_with_pr_github_url() -> None:
    """Test formatting PR cell with PR info using GitHub URL."""
    pr = PullRequestInfo(
        number=123,
        state="OPEN",
        is_draft=False,
        url="https://github.com/owner/repo/pull/123",
        owner="owner",
        repo="repo",
        title="Add feature",
        checks_passing=None,
    )

    result = _format_pr_cell(pr, use_graphite=False, graphite_url=None)

    assert "#123" in result
    assert "👀" in result  # Default open PR emoji
    assert "[link=" in result  # Has Rich link markup
    assert "https://github.com/owner/repo/pull/123" in result


def test_format_pr_cell_with_planned_pr() -> None:
    """Test formatting PR cell with draft PR."""
    pr = PullRequestInfo(
        number=456,
        state="OPEN",
        is_draft=True,
        url="https://github.com/owner/repo/pull/456",
        owner="owner",
        repo="repo",
        title="WIP: Feature",
        checks_passing=None,
    )

    result = _format_pr_cell(pr, use_graphite=False, graphite_url=None)

    assert "#456" in result
    assert "🚧" in result  # Draft PR emoji


def test_format_pr_cell_with_merged_pr() -> None:
    """Test formatting PR cell with merged PR."""
    pr = PullRequestInfo(
        number=789,
        state="MERGED",
        is_draft=False,
        url="https://github.com/owner/repo/pull/789",
        owner="owner",
        repo="repo",
        title="Merged feature",
        checks_passing=None,
    )

    result = _format_pr_cell(pr, use_graphite=False, graphite_url=None)

    assert "#789" in result
    assert "🎉" in result  # Merged PR emoji


def test_format_pr_cell_none() -> None:
    """Test formatting PR cell with no PR."""
    result = _format_pr_cell(None, use_graphite=False, graphite_url=None)

    assert result == "-"


def test_format_impl_cell_with_url() -> None:
    """Test formatting impl cell with URL makes it clickable."""
    result = _format_impl_cell("#42", "https://github.com/owner/repo/issues/42")

    assert "#42" in result
    assert "[link=" in result
    assert "https://github.com/owner/repo/issues/42" in result


def test_format_impl_cell_without_url() -> None:
    """Test formatting impl cell without URL shows plain text."""
    result = _format_impl_cell("#123", None)

    assert result == "#123"
    assert "[link=" not in result


def test_format_impl_cell_none() -> None:
    """Test formatting impl cell with no issue."""
    result = _format_impl_cell(None, None)

    assert result == "-"


def test_format_sync_from_batch_current() -> None:
    """Test sync status from batch returns 'current' when branch is up-to-date."""
    all_sync = {
        "feature": BranchSyncInfo(branch="feature", upstream="origin/feature", ahead=0, behind=0)
    }

    result = _format_sync_from_batch(all_sync, "feature")

    assert result == "current"


def test_format_sync_from_batch_ahead_only() -> None:
    """Test sync status from batch returns 'N↑' when ahead only."""
    all_sync = {
        "feature": BranchSyncInfo(branch="feature", upstream="origin/feature", ahead=3, behind=0)
    }

    result = _format_sync_from_batch(all_sync, "feature")

    assert result == "3↑"


def test_format_sync_from_batch_behind_only() -> None:
    """Test sync status from batch returns 'N↓' when behind only."""
    all_sync = {
        "feature": BranchSyncInfo(branch="feature", upstream="origin/feature", ahead=0, behind=2)
    }

    result = _format_sync_from_batch(all_sync, "feature")

    assert result == "2↓"


def test_format_sync_from_batch_ahead_and_behind() -> None:
    """Test sync status from batch returns 'N↑ M↓' when both ahead and behind."""
    all_sync = {
        "feature": BranchSyncInfo(branch="feature", upstream="origin/feature", ahead=5, behind=3)
    }

    result = _format_sync_from_batch(all_sync, "feature")

    assert result == "5↑ 3↓"


def test_format_sync_from_batch_none_branch() -> None:
    """Test sync status from batch returns '-' when branch is None (detached HEAD)."""
    all_sync: dict[str, BranchSyncInfo] = {}

    result = _format_sync_from_batch(all_sync, None)

    assert result == "-"


def test_format_sync_from_batch_branch_not_found() -> None:
    """Test sync status from batch returns '-' when branch not in dict."""
    all_sync = {
        "other-branch": BranchSyncInfo(
            branch="other-branch", upstream="origin/other-branch", ahead=0, behind=0
        )
    }

    result = _format_sync_from_batch(all_sync, "feature")

    assert result == "-"


def test_format_sync_from_batch_no_upstream() -> None:
    """Test sync status from batch returns 'current' when no upstream tracking."""
    all_sync = {"feature": BranchSyncInfo(branch="feature", upstream=None, ahead=0, behind=0)}

    result = _format_sync_from_batch(all_sync, "feature")

    assert result == "current"


def test_format_last_commit_cell_with_valid_timestamp() -> None:
    """Test formatting last commit cell with valid timestamp returns relative time."""
    repo_root = Path("/repo")
    # Create a timestamp from 2 days ago
    two_days_ago = datetime.now(UTC) - timedelta(days=2)
    timestamp = two_days_ago.isoformat()

    git = FakeGit(
        branch_last_commit_times={(repo_root, "feature", "main"): timestamp},
    )
    ctx = create_test_context(git=git)

    result = _format_last_commit_cell(ctx, repo_root, "feature", "main")

    assert result == "2d ago"


def test_format_last_commit_cell_with_none_branch() -> None:
    """Test formatting last commit cell returns '-' when branch is None (detached HEAD)."""
    repo_root = Path("/repo")
    git = FakeGit()
    ctx = create_test_context(git=git)

    result = _format_last_commit_cell(ctx, repo_root, None, "main")

    assert result == "-"


def test_format_last_commit_cell_with_trunk_branch() -> None:
    """Test formatting last commit cell returns '-' when branch is trunk."""
    repo_root = Path("/repo")
    git = FakeGit()
    ctx = create_test_context(git=git)

    result = _format_last_commit_cell(ctx, repo_root, "main", "main")

    assert result == "-"


def test_format_last_commit_cell_no_unique_commits() -> None:
    """Test formatting last commit cell returns '-' when no unique commits."""
    repo_root = Path("/repo")
    git = FakeGit(
        branch_last_commit_times={},  # No entry for branch means no unique commits
    )
    ctx = create_test_context(git=git)

    result = _format_last_commit_cell(ctx, repo_root, "feature", "main")

    assert result == "-"
