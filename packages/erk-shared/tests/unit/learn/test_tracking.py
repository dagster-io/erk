"""Tests for learn tracking functions."""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.learn.tracking import track_learn_invocation
from tests.test_utils.plan_helpers import create_backend_from_issues


def _create_test_issue(number: int, title: str, body: str) -> IssueInfo:
    """Create a minimal test issue."""
    now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=None,
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


def test_track_learn_invocation_posts_comment() -> None:
    """Track invocation posts comment to plan PR."""
    issue = _create_test_issue(number=42, title="Plan", body="content")
    backend, fake_github, _ = create_backend_from_issues({42: issue})

    track_learn_invocation(
        backend,
        Path("/repo"),
        "42",
        session_id="test-session-123",
        readable_count=2,
        total_count=3,
    )

    # Verify comment was added to the plan PR
    assert len(fake_github.pr_comments) == 1
    pr_num, comment_body = fake_github.pr_comments[0]
    assert pr_num == 42
    assert "learn-invoked" in comment_body
    assert "test-session-123" in comment_body


def test_track_learn_invocation_without_session_id() -> None:
    """Track invocation works without session ID."""
    issue = _create_test_issue(number=42, title="Plan", body="content")
    backend, fake_github, _ = create_backend_from_issues({42: issue})

    track_learn_invocation(
        backend,
        Path("/repo"),
        "42",
        session_id=None,
        readable_count=0,
        total_count=1,
    )

    # Verify comment was added
    assert len(fake_github.pr_comments) == 1
    _pr_num, comment_body = fake_github.pr_comments[0]
    assert "learn-invoked" in comment_body
    assert "No readable sessions" in comment_body


def test_track_learn_invocation_includes_counts() -> None:
    """Track invocation includes session counts in description."""
    issue = _create_test_issue(number=42, title="Plan", body="content")
    backend, fake_github, _ = create_backend_from_issues({42: issue})

    track_learn_invocation(
        backend,
        Path("/repo"),
        "42",
        session_id="session-abc",
        readable_count=5,
        total_count=8,
    )

    _pr_num, comment_body = fake_github.pr_comments[0]
    assert "5 readable sessions" in comment_body
    assert "8 total" in comment_body
