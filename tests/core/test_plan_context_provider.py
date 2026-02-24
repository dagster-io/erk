"""Tests for PlanContextProvider."""

from datetime import UTC, datetime
from pathlib import Path

from erk.core.plan_context_provider import PlanContext, PlanContextProvider
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.metadata.plan_header import (
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.plan_store.github import GitHubPlanStore


def _make_issue_info(
    *,
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create an IssueInfo for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_provider(github_issues: FakeGitHubIssues) -> PlanContextProvider:
    """Create a PlanContextProvider with GitHubPlanStore backed by fake issues."""
    plan_backend = GitHubPlanStore(github_issues)
    return PlanContextProvider(plan_backend=plan_backend, github_issues=github_issues)


def test_get_plan_context_returns_none_for_non_plan_branch(tmp_path: Path) -> None:
    """Test that branches without issue number prefix return None."""
    provider = _make_provider(FakeGitHubIssues())

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="feature-branch",
    )

    assert result is None


def test_get_plan_context_returns_none_for_missing_issue(tmp_path: Path) -> None:
    """Test that branches return None when branch-based resolution no longer works.

    Since extract_leading_issue_number() now always returns None, P-prefix branches
    can no longer be resolved to plan IDs from the branch name alone.
    """
    provider = _make_provider(FakeGitHubIssues(issues={}))

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="P123-fix-bug",
    )

    assert result is None


def test_get_plan_context_returns_content_for_old_format_issue(tmp_path: Path) -> None:
    """Test that branch-based resolution returns None since it's no longer supported.

    Since extract_leading_issue_number() always returns None, P-prefix branches
    cannot resolve to plan IDs, even when the issue exists.
    """
    issue = _make_issue_info(
        number=123,
        title="Regular Issue",
        body="This is just a regular issue body",
    )
    provider = _make_provider(FakeGitHubIssues(issues={123: issue}))

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="P123-fix-bug",
    )

    # Branch-based resolution no longer works
    assert result is None


def test_get_plan_context_falls_back_to_body_for_missing_comment(tmp_path: Path) -> None:
    """Test that branch-based resolution returns None since it's no longer supported.

    Even when the issue exists and has plan metadata, P-prefix branches cannot
    resolve to plan IDs because extract_leading_issue_number() always returns None.
    """
    body = format_plan_header_body(
        created_at="2024-01-01T00:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=1000,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    issue = _make_issue_info(number=123, title="Plan: Fix bug", body=body)
    provider = _make_provider(FakeGitHubIssues(issues={123: issue}))

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="P123-fix-bug",
    )

    # Branch-based resolution no longer works
    assert result is None


def test_get_plan_context_extracts_plan_content(tmp_path: Path) -> None:
    """Test that branch-based resolution returns None since it's no longer supported.

    Even with a complete plan issue and comment, P-prefix branches cannot resolve
    to plan IDs because extract_leading_issue_number() always returns None.
    """
    plan_content = """# Plan: Fix Authentication Bug

## Problem
Users are getting logged out unexpectedly.

## Solution
Fix the session token expiration logic."""

    comment_body = format_plan_content_comment(plan_content)

    body = format_plan_header_body(
        created_at="2024-01-01T00:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=1000,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    issue = _make_issue_info(number=123, title="Plan: Fix Authentication Bug", body=body)

    comment = IssueComment(
        id=1000,
        body=comment_body,
        url="https://github.com/test-owner/test-repo/issues/123#issuecomment-1000",
        author="testuser",
    )

    github_issues = FakeGitHubIssues(
        issues={123: issue},
        comments_with_urls={123: [comment]},
    )
    provider = _make_provider(github_issues)

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="P123-fix-auth-bug",
    )

    # Branch-based resolution no longer works
    assert result is None


def test_get_plan_context_includes_objective_summary(tmp_path: Path) -> None:
    """Test that branch-based resolution returns None since it's no longer supported.

    Even when a plan is linked to an objective, P-prefix branches cannot resolve
    to plan IDs because extract_leading_issue_number() always returns None.
    """
    plan_content = "# Plan: Implement Feature\n\nDetails here."
    comment_body = format_plan_content_comment(plan_content)

    plan_body = format_plan_header_body(
        created_at="2024-01-01T00:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=1000,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=200,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    plan_issue = _make_issue_info(number=123, title="Plan: Implement Feature", body=plan_body)

    objective_issue = _make_issue_info(
        number=200,
        title="Improve CI Reliability",
        body="Objective body",
    )

    comment = IssueComment(
        id=1000,
        body=comment_body,
        url="https://github.com/test-owner/test-repo/issues/123#issuecomment-1000",
        author="testuser",
    )

    github_issues = FakeGitHubIssues(
        issues={123: plan_issue, 200: objective_issue},
        comments_with_urls={123: [comment]},
    )
    provider = _make_provider(github_issues)

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="P123-implement-feature",
    )

    # Branch-based resolution no longer works
    assert result is None


def test_get_plan_context_handles_missing_objective(tmp_path: Path) -> None:
    """Test that branch-based resolution returns None since it's no longer supported.

    Even when a plan references a missing objective, P-prefix branches cannot
    resolve to plan IDs because extract_leading_issue_number() always returns None.
    """
    plan_content = "# Plan: Implement Feature\n\nDetails here."
    comment_body = format_plan_content_comment(plan_content)

    plan_body = format_plan_header_body(
        created_at="2024-01-01T00:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=1000,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=999,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    plan_issue = _make_issue_info(number=123, title="Plan: Implement Feature", body=plan_body)

    comment = IssueComment(
        id=1000,
        body=comment_body,
        url="https://github.com/test-owner/test-repo/issues/123#issuecomment-1000",
        author="testuser",
    )

    github_issues = FakeGitHubIssues(
        issues={123: plan_issue},
        comments_with_urls={123: [comment]},
    )
    provider = _make_provider(github_issues)

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="P123-implement-feature",
    )

    # Branch-based resolution no longer works
    assert result is None


def test_get_plan_context_supports_legacy_branch_format(tmp_path: Path) -> None:
    """Test that branch-based resolution returns None for legacy format too.

    Even plain numeric-prefixed branches (without P) cannot resolve to plan IDs
    because extract_leading_issue_number() always returns None.
    """
    plan_content = "# Plan: Fix Bug\n\nDetails."
    comment_body = format_plan_content_comment(plan_content)

    plan_body = format_plan_header_body(
        created_at="2024-01-01T00:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=1000,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    issue = _make_issue_info(number=456, title="Plan: Fix Bug", body=plan_body)
    comment = IssueComment(
        id=1000,
        body=comment_body,
        url="https://github.com/test-owner/test-repo/issues/456#issuecomment-1000",
        author="testuser",
    )

    github_issues = FakeGitHubIssues(
        issues={456: issue},
        comments_with_urls={456: [comment]},
    )
    provider = _make_provider(github_issues)

    result = provider.get_plan_context(
        repo_root=tmp_path,
        branch_name="456-fix-bug",
    )

    # Branch-based resolution no longer works
    assert result is None


def test_plan_context_dataclass_frozen() -> None:
    """Test that PlanContext is immutable (frozen dataclass)."""
    context = PlanContext(
        plan_id="123",
        plan_content="Plan content",
        objective_summary="Objective #1: Test",
    )

    assert context.plan_id == "123"
    assert context.plan_content == "Plan content"
    assert context.objective_summary == "Objective #1: Test"

    try:
        context.plan_id = "456"  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except AttributeError:
        pass
