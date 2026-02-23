"""Tests for GitHubPlanStore.update_plan_content resilience.

Verifies the self-healing behavior when update_plan_content encounters
an issue with no existing plan comment — it creates one instead of raising.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_comment_id,
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.plan_store.github import GitHubPlanStore


def _make_plan_header_body(*, plan_comment_id: int | None) -> str:
    """Create a minimal plan-header body for testing."""
    return format_plan_header_body(
        created_at="2024-01-01T00:00:00+00:00",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=plan_comment_id,
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


def _make_issue(number: int, body: str) -> IssueInfo:
    now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title="Test Plan",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_update_plan_content_creates_comment_when_none_exist() -> None:
    """When no plan comment exists, update_plan_content creates one and updates body."""
    body = _make_plan_header_body(plan_comment_id=None)
    issue = _make_issue(42, body)

    # No comments configured — neither comments nor comments_with_urls
    issues = FakeGitHubIssues(issues={42: issue})
    store = GitHubPlanStore(issues)

    store.update_plan_content(Path("/repo"), "42", "# Updated Plan\n\nNew content")

    # A comment was added via add_comment
    assert len(issues.added_comments) == 1
    issue_number, comment_body, _comment_id = issues.added_comments[0]
    assert issue_number == 42
    # The comment should be formatted as a plan-body block
    assert "plan-body" in comment_body
    assert "Updated Plan" in comment_body

    # The issue body was updated with plan_comment_id
    assert len(issues.updated_bodies) == 1
    _, updated_body = issues.updated_bodies[0]
    comment_id = extract_plan_header_comment_id(updated_body)
    assert comment_id is not None


def test_update_plan_content_first_comment_fallback_still_works() -> None:
    """When plan_comment_id is None but first comment exists, update it (not create new)."""
    body = _make_plan_header_body(plan_comment_id=None)
    issue = _make_issue(42, body)

    # Pre-existing first comment (the fallback path)
    existing_comment = IssueComment(
        id=500,
        body=format_plan_content_comment("# Old Plan"),
        url="https://github.com/test/repo/issues/42#issuecomment-500",
        author="testuser",
    )
    issues = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [existing_comment]},
    )
    store = GitHubPlanStore(issues)

    store.update_plan_content(Path("/repo"), "42", "# Newer Plan\n\nNew content")

    # Existing comment was updated (not a new comment created)
    assert len(issues.added_comments) == 0
    assert len(issues.updated_comments) == 1
    comment_id, updated_body = issues.updated_comments[0]
    assert comment_id == 500
    assert "Newer Plan" in updated_body
