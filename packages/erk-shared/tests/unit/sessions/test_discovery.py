"""Tests for session discovery functions."""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.metadata.types import MetadataBlock
from erk_shared.sessions.discovery import (
    SessionsForPlan,
    find_sessions_for_plan,
)


def _create_test_issue(
    *,
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create a test IssueInfo with sensible defaults."""
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        author="test-user",
    )


def _make_impl_comment(event: str, session_id: str) -> str:
    """Create a test implementation event comment."""
    block = MetadataBlock(
        key=f"impl-{event}",
        data={"session_id": session_id, "timestamp": "2024-01-15T10:00:00Z"},
    )
    return render_metadata_block(block)


def _make_learn_comment(session_id: str) -> str:
    """Create a test learn event comment."""
    block = MetadataBlock(
        key="learn-invoked",
        data={"session_id": session_id, "timestamp": "2024-01-15T12:00:00Z"},
    )
    return render_metadata_block(block)


def test_sessions_for_plan_all_session_ids_empty() -> None:
    """All session IDs returns empty for empty object."""
    sessions = SessionsForPlan(
        planning_session_id=None,
        implementation_session_ids=[],
        learn_session_ids=[],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
    )
    assert sessions.all_session_ids() == []


def test_sessions_for_plan_all_session_ids_planning_only() -> None:
    """All session IDs includes planning session first."""
    sessions = SessionsForPlan(
        planning_session_id="planning-123",
        implementation_session_ids=[],
        learn_session_ids=[],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
    )
    assert sessions.all_session_ids() == ["planning-123"]


def test_sessions_for_plan_all_session_ids_deduplicates() -> None:
    """All session IDs deduplicates across categories."""
    sessions = SessionsForPlan(
        planning_session_id="shared-session",
        implementation_session_ids=["shared-session", "impl-only"],
        learn_session_ids=["learn-only", "shared-session"],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
    )
    # shared-session should only appear once (from planning)
    result = sessions.all_session_ids()
    assert result == ["shared-session", "impl-only", "learn-only"]


def test_sessions_for_plan_all_session_ids_order() -> None:
    """All session IDs returns in logical order: planning, impl, learn."""
    sessions = SessionsForPlan(
        planning_session_id="plan-session",
        implementation_session_ids=["impl-1", "impl-2"],
        learn_session_ids=["learn-1"],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
    )
    result = sessions.all_session_ids()
    assert result == ["plan-session", "impl-1", "impl-2", "learn-1"]


def _make_plan_body(
    *,
    created_from_session: str | None = None,
    last_local_impl_session: str | None = None,
    last_remote_impl_at: str | None = None,
) -> str:
    """Create a plan-header body for testing."""
    return format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=last_local_impl_session,
        last_local_impl_user=None,
        last_remote_impl_at=last_remote_impl_at,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=created_from_session,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )


def test_find_sessions_for_plan_no_sessions() -> None:
    """Find sessions returns empty collections when no sessions exist."""
    # Issue body without created_from_session
    body = _make_plan_body()
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.planning_session_id is None
    assert result.implementation_session_ids == []
    assert result.learn_session_ids == []
    assert result.last_remote_impl_at is None


def test_find_sessions_for_plan_with_created_from_session() -> None:
    """Find sessions extracts planning session from metadata."""
    body = _make_plan_body(created_from_session="planning-session-abc")
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.planning_session_id == "planning-session-abc"


def test_find_sessions_for_plan_with_impl_session_in_metadata() -> None:
    """Find sessions extracts implementation session from plan-header."""
    body = _make_plan_body(last_local_impl_session="impl-session-xyz")
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.implementation_session_ids == ["impl-session-xyz"]


def test_find_sessions_for_plan_with_impl_comments() -> None:
    """Find sessions extracts sessions from impl comments."""
    body = _make_plan_body()
    issue = _create_test_issue(number=42, title="Plan", body=body)
    comments = [
        _make_impl_comment("started", "impl-comment-session"),
        _make_impl_comment("ended", "impl-comment-session"),
    ]
    fake_gh = FakeGitHubIssues(issues={42: issue}, comments={42: comments})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    # Should deduplicate the same session from started/ended
    assert result.implementation_session_ids == ["impl-comment-session"]


def test_find_sessions_for_plan_with_learn_comments() -> None:
    """Find sessions extracts sessions from learn comments."""
    body = _make_plan_body()
    issue = _create_test_issue(number=42, title="Plan", body=body)
    comments = [
        _make_learn_comment("learn-session-1"),
        _make_learn_comment("learn-session-2"),
    ]
    fake_gh = FakeGitHubIssues(issues={42: issue}, comments={42: comments})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.learn_session_ids == ["learn-session-1", "learn-session-2"]


def test_find_sessions_for_plan_combines_all_sources() -> None:
    """Find sessions combines metadata and comments."""
    body = _make_plan_body(
        created_from_session="planning-session",
        last_local_impl_session="metadata-impl-session",
    )
    issue = _create_test_issue(number=42, title="Plan", body=body)
    comments = [
        _make_impl_comment("started", "comment-impl-session"),
        _make_learn_comment("learn-session"),
    ]
    fake_gh = FakeGitHubIssues(issues={42: issue}, comments={42: comments})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.planning_session_id == "planning-session"
    # Metadata impl session comes first, then from comments
    assert result.implementation_session_ids == [
        "metadata-impl-session",
        "comment-impl-session",
    ]
    assert result.learn_session_ids == ["learn-session"]


def test_find_sessions_for_plan_with_remote_impl() -> None:
    """Find sessions extracts last_remote_impl_at from plan-header."""
    body = _make_plan_body(last_remote_impl_at="2024-01-16T14:30:00Z")
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.last_remote_impl_at == "2024-01-16T14:30:00Z"
    # No local implementation sessions
    assert result.implementation_session_ids == []


def test_find_sessions_for_plan_with_both_local_and_remote_impl() -> None:
    """Find sessions returns both local sessions and remote timestamp."""
    body = _make_plan_body(
        last_local_impl_session="local-impl-session",
        last_remote_impl_at="2024-01-16T14:30:00Z",
    )
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    # Both should be present
    assert result.implementation_session_ids == ["local-impl-session"]
    assert result.last_remote_impl_at == "2024-01-16T14:30:00Z"


def _make_plan_body_with_remote_impl(
    *,
    last_remote_impl_at: str | None = None,
    last_remote_impl_run_id: str | None = None,
    last_remote_impl_session_id: str | None = None,
) -> str:
    """Create a plan-header body with remote implementation fields."""
    return format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=last_remote_impl_at,
        last_remote_impl_run_id=last_remote_impl_run_id,
        last_remote_impl_session_id=last_remote_impl_session_id,
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
    )


def test_find_sessions_for_plan_with_remote_impl_run_id() -> None:
    """Find sessions extracts last_remote_impl_run_id from plan-header."""
    body = _make_plan_body_with_remote_impl(
        last_remote_impl_at="2024-01-16T14:30:00Z",
        last_remote_impl_run_id="12345678",
    )
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.last_remote_impl_at == "2024-01-16T14:30:00Z"
    assert result.last_remote_impl_run_id == "12345678"
    assert result.last_remote_impl_session_id is None


def test_find_sessions_for_plan_with_remote_impl_session_id() -> None:
    """Find sessions extracts last_remote_impl_session_id from plan-header."""
    body = _make_plan_body_with_remote_impl(
        last_remote_impl_at="2024-01-16T14:30:00Z",
        last_remote_impl_run_id="12345678",
        last_remote_impl_session_id="remote-session-abc",
    )
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.last_remote_impl_at == "2024-01-16T14:30:00Z"
    assert result.last_remote_impl_run_id == "12345678"
    assert result.last_remote_impl_session_id == "remote-session-abc"


def test_find_sessions_for_plan_remote_fields_none_by_default() -> None:
    """Find sessions returns None for remote fields when not set."""
    body = _make_plan_body()
    issue = _create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.last_remote_impl_at is None
    assert result.last_remote_impl_run_id is None
    assert result.last_remote_impl_session_id is None
