"""Tests for learn tracking functions."""

from pathlib import Path

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.tracking import track_learn_invocation
from tests.test_utils.github_helpers import create_test_issue


def test_track_learn_invocation_posts_comment() -> None:
    """Track invocation posts comment to issue."""
    issue = create_test_issue(number=42, title="Plan", body="content")
    fake_gh = FakeGitHubIssues(issues={42: issue})

    track_learn_invocation(
        fake_gh,
        Path("/repo"),
        42,
        session_id="test-session-123",
        readable_count=2,
        total_count=3,
    )

    # Verify comment was added
    assert len(fake_gh.added_comments) == 1
    issue_num, comment_body, _comment_id = fake_gh.added_comments[0]
    assert issue_num == 42
    assert "learn-invoked" in comment_body
    assert "test-session-123" in comment_body


def test_track_learn_invocation_without_session_id() -> None:
    """Track invocation works without session ID."""
    issue = create_test_issue(number=42, title="Plan", body="content")
    fake_gh = FakeGitHubIssues(issues={42: issue})

    track_learn_invocation(
        fake_gh,
        Path("/repo"),
        42,
        session_id=None,
        readable_count=0,
        total_count=1,
    )

    # Verify comment was added
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "learn-invoked" in comment_body
    assert "No readable sessions" in comment_body


def test_track_learn_invocation_includes_counts() -> None:
    """Track invocation includes session counts in description."""
    issue = create_test_issue(number=42, title="Plan", body="content")
    fake_gh = FakeGitHubIssues(issues={42: issue})

    track_learn_invocation(
        fake_gh,
        Path("/repo"),
        42,
        session_id="session-abc",
        readable_count=5,
        total_count=8,
    )

    _issue_num, comment_body, _comment_id = fake_gh.added_comments[0]
    assert "5 readable sessions" in comment_body
    assert "8 total" in comment_body
