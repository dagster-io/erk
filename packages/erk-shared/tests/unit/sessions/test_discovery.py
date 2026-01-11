"""Tests for session discovery functions."""

from pathlib import Path

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata.core import render_metadata_block
from erk_shared.github.metadata.plan_header import format_plan_header_body
from erk_shared.github.metadata.types import MetadataBlock
from erk_shared.sessions.discovery import (
    SessionsForPlan,
    find_sessions_for_plan,
)
from tests.test_utils.github_helpers import create_test_issue


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
    )
    assert sessions.all_session_ids() == []


def test_sessions_for_plan_all_session_ids_planning_only() -> None:
    """All session IDs includes planning session first."""
    sessions = SessionsForPlan(
        planning_session_id="planning-123",
        implementation_session_ids=[],
        learn_session_ids=[],
    )
    assert sessions.all_session_ids() == ["planning-123"]


def test_sessions_for_plan_all_session_ids_deduplicates() -> None:
    """All session IDs deduplicates across categories."""
    sessions = SessionsForPlan(
        planning_session_id="shared-session",
        implementation_session_ids=["shared-session", "impl-only"],
        learn_session_ids=["learn-only", "shared-session"],
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
    )
    result = sessions.all_session_ids()
    assert result == ["plan-session", "impl-1", "impl-2", "learn-1"]


def test_find_sessions_for_plan_no_sessions() -> None:
    """Find sessions returns empty collections when no sessions exist."""
    # Issue body without created_from_session
    body = format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
    )
    issue = create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.planning_session_id is None
    assert result.implementation_session_ids == []
    assert result.learn_session_ids == []


def test_find_sessions_for_plan_with_created_from_session() -> None:
    """Find sessions extracts planning session from metadata."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
        created_from_session="planning-session-abc",
    )
    issue = create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.planning_session_id == "planning-session-abc"


def test_find_sessions_for_plan_with_impl_session_in_metadata() -> None:
    """Find sessions extracts implementation session from plan-header."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
        last_local_impl_session="impl-session-xyz",
    )
    issue = create_test_issue(number=42, title="Plan", body=body)
    fake_gh = FakeGitHubIssues(issues={42: issue})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.implementation_session_ids == ["impl-session-xyz"]


def test_find_sessions_for_plan_with_impl_comments() -> None:
    """Find sessions extracts sessions from impl comments."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
    )
    issue = create_test_issue(number=42, title="Plan", body=body)
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
    body = format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
    )
    issue = create_test_issue(number=42, title="Plan", body=body)
    comments = [
        _make_learn_comment("learn-session-1"),
        _make_learn_comment("learn-session-2"),
    ]
    fake_gh = FakeGitHubIssues(issues={42: issue}, comments={42: comments})

    result = find_sessions_for_plan(fake_gh, Path("/repo"), 42)

    assert result.learn_session_ids == ["learn-session-1", "learn-session-2"]


def test_find_sessions_for_plan_combines_all_sources() -> None:
    """Find sessions combines metadata and comments."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:00:00Z",
        created_by="testuser",
        created_from_session="planning-session",
        last_local_impl_session="metadata-impl-session",
    )
    issue = create_test_issue(number=42, title="Plan", body=body)
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
