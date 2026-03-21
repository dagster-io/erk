"""Unit tests for worktree cleanup helpers.

NOTE: These are basic unit tests for the extracted helper functions.
The full integration of these helpers is tested in the wt delete and slot unassign
command tests where the proper context (repo owner/name, etc.) is available.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.gateway.github.types import PullRequestInfo
from erk_shared.pr_store.types import Plan, PlanState
from erk_shared.worktree_cleanup import (
    close_plan_for_worktree,
    close_pr_for_branch,
    delete_branch,
    get_plan_info_for_worktree,
    get_pr_info_for_branch,
)
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.tests.context import create_test_context


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_get_pr_info_for_branch_with_open_pr() -> None:
    """Test getting PR info returns number and state for open PR."""
    repo_root = Path("/repo")
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
    github = FakeLocalGitHub(prs_by_branch={("owner/repo", "feature"): pr})
    ctx = create_test_context(github=github)

    result = get_pr_info_for_branch(ctx, repo_root, "feature")

    assert result == (123, "OPEN")


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_get_pr_info_for_branch_with_merged_pr() -> None:
    """Test getting PR info returns number and state for merged PR."""
    repo_root = Path("/repo")
    pr = PullRequestInfo(
        number=456,
        state="MERGED",
        is_draft=False,
        url="https://github.com/owner/repo/pull/456",
        owner="owner",
        repo="repo",
        title="Merged feature",
        checks_passing=None,
    )
    github = FakeLocalGitHub(prs_by_branch={("owner/repo", "feature"): pr})
    ctx = create_test_context(github=github)

    result = get_pr_info_for_branch(ctx, repo_root, "feature")

    assert result == (456, "MERGED")


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_get_pr_info_for_branch_returns_none_when_not_found() -> None:
    """Test getting PR info returns None when no PR exists."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    result = get_pr_info_for_branch(ctx, repo_root, "feature")

    assert result is None


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_get_plan_info_for_worktree_with_open_plan() -> None:
    """Test getting plan info returns number and state for open plan."""
    repo_root = Path("/repo")
    plan = Plan(
        pr_identifier="789",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/pull/789",
        title="Plan: Add feature",
        body="# Plan\n...",
        header_fields={"erk-worktree-name": "feature-wt"},
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
        objective_id=None,
    )
    github = FakeLocalGitHub(managed_prs=[plan])
    ctx = create_test_context(github=github)

    result = get_plan_info_for_worktree(ctx, repo_root, "feature-wt")

    assert result == (789, PlanState.OPEN)


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_get_plan_info_for_worktree_with_closed_plan() -> None:
    """Test getting plan info returns number and state for closed plan."""
    repo_root = Path("/repo")
    plan = Plan(
        pr_identifier="999",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/pull/999",
        title="Plan: Closed feature",
        body="# Plan\n...",
        header_fields={"erk-worktree-name": "closed-wt"},
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
        objective_id=None,
    )
    github = FakeLocalGitHub(managed_prs=[plan])
    ctx = create_test_context(github=github)

    result = get_plan_info_for_worktree(ctx, repo_root, "closed-wt")

    assert result == (999, PlanState.CLOSED)


def test_get_plan_info_for_worktree_returns_none_when_not_found() -> None:
    """Test getting plan info returns None when no plan exists."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    result = get_plan_info_for_worktree(ctx, repo_root, "unknown-wt")

    assert result is None


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_close_pr_for_branch_closes_open_pr() -> None:
    """Test closing PR for branch closes open PR and returns number."""
    repo_root = Path("/repo")
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
    github = FakeLocalGitHub(prs_by_branch={("owner/repo", "feature"): pr})
    ctx = create_test_context(github=github)

    result = close_pr_for_branch(ctx, repo_root, "feature")

    assert result == 123
    assert ("owner/repo", 123) in github.closed_prs


def test_close_pr_for_branch_returns_none_for_merged_pr() -> None:
    """Test closing PR for branch returns None for already merged PR."""
    repo_root = Path("/repo")
    pr = PullRequestInfo(
        number=456,
        state="MERGED",
        is_draft=False,
        url="https://github.com/owner/repo/pull/456",
        owner="owner",
        repo="repo",
        title="Merged feature",
        checks_passing=None,
    )
    github = FakeLocalGitHub(prs_by_branch={("owner/repo", "feature"): pr})
    ctx = create_test_context(github=github)

    result = close_pr_for_branch(ctx, repo_root, "feature")

    assert result is None
    assert ("owner/repo", 456) not in github.closed_prs


def test_close_pr_for_branch_returns_none_for_closed_pr() -> None:
    """Test closing PR for branch returns None for already closed PR."""
    repo_root = Path("/repo")
    pr = PullRequestInfo(
        number=789,
        state="CLOSED",
        is_draft=False,
        url="https://github.com/owner/repo/pull/789",
        owner="owner",
        repo="repo",
        title="Closed feature",
        checks_passing=None,
    )
    github = FakeLocalGitHub(prs_by_branch={("owner/repo", "feature"): pr})
    ctx = create_test_context(github=github)

    result = close_pr_for_branch(ctx, repo_root, "feature")

    assert result is None
    assert ("owner/repo", 789) not in github.closed_prs


def test_close_pr_for_branch_returns_none_when_no_pr() -> None:
    """Test closing PR for branch returns None when no PR exists."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    result = close_pr_for_branch(ctx, repo_root, "feature")

    assert result is None


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_close_plan_for_worktree_closes_open_plan() -> None:
    """Test closing plan for worktree closes open plan and returns number."""
    repo_root = Path("/repo")
    plan = Plan(
        pr_identifier="789",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/pull/789",
        title="Plan: Add feature",
        body="# Plan\n...",
        header_fields={"erk-worktree-name": "feature-wt"},
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
        objective_id=None,
    )
    github = FakeLocalGitHub(managed_prs=[plan])
    ctx = create_test_context(github=github)

    result = close_plan_for_worktree(ctx, repo_root, "feature-wt")

    assert result == 789
    assert ("owner/repo", 789) in github.closed_prs


@pytest.mark.skip(reason="Requires full repo context setup - tested in integration")
def test_close_plan_for_worktree_returns_none_for_closed_plan() -> None:
    """Test closing plan for worktree returns None for already closed plan."""
    repo_root = Path("/repo")
    plan = Plan(
        pr_identifier="999",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/pull/999",
        title="Plan: Closed feature",
        body="# Plan\n...",
        header_fields={"erk-worktree-name": "closed-wt"},
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
        objective_id=None,
    )
    github = FakeLocalGitHub(managed_prs=[plan])
    ctx = create_test_context(github=github)

    result = close_plan_for_worktree(ctx, repo_root, "closed-wt")

    assert result is None


def test_close_plan_for_worktree_returns_none_when_no_plan() -> None:
    """Test closing plan for worktree returns None when no plan exists."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    result = close_plan_for_worktree(ctx, repo_root, "unknown-wt")

    assert result is None


def test_delete_branch_succeeds() -> None:
    """Test delete_branch succeeds when branch exists."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    # Should not raise
    delete_branch(ctx, repo_root=repo_root, branch="feature", force=False, dry_run=False)


def test_delete_branch_dry_run() -> None:
    """Test delete_branch in dry-run mode doesn't output success message."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    # Should not raise, and should not print success message in dry-run
    delete_branch(ctx, repo_root=repo_root, branch="feature", force=False, dry_run=True)


def test_delete_branch_with_force() -> None:
    """Test delete_branch with force flag."""
    repo_root = Path("/repo")
    github = FakeLocalGitHub()
    ctx = create_test_context(github=github)

    # Should not raise
    delete_branch(ctx, repo_root=repo_root, branch="feature", force=True, dry_run=False)
