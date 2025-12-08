"""Tests for PR review thread functionality in GitHub layer."""

from pathlib import Path

from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRReviewComment, PRReviewThread


def test_fake_get_pr_review_threads_returns_configured_threads() -> None:
    """Test that FakeGitHub returns pre-configured review threads."""
    comment = PRReviewComment(
        id=1,
        body="This should use LBYL pattern",
        author="reviewer",
        path="src/foo.py",
        line=42,
        created_at="2024-01-01T10:00:00Z",
    )
    thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=42,
        is_resolved=False,
        is_outdated=False,
        comments=(comment,),
    )

    github = FakeGitHub(pr_review_threads={123: [thread]})

    threads = github.get_pr_review_threads(Path("/repo"), 123)

    assert len(threads) == 1
    assert threads[0].id == "PRRT_1"
    assert threads[0].path == "src/foo.py"
    assert threads[0].line == 42
    assert not threads[0].is_resolved
    assert len(threads[0].comments) == 1
    assert threads[0].comments[0].author == "reviewer"


def test_fake_get_pr_review_threads_filters_resolved_by_default() -> None:
    """Test that resolved threads are excluded by default."""
    unresolved_thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=10,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )
    resolved_thread = PRReviewThread(
        id="PRRT_2",
        path="src/bar.py",
        line=20,
        is_resolved=True,
        is_outdated=False,
        comments=(),
    )

    github = FakeGitHub(pr_review_threads={123: [unresolved_thread, resolved_thread]})

    threads = github.get_pr_review_threads(Path("/repo"), 123)

    assert len(threads) == 1
    assert threads[0].id == "PRRT_1"


def test_fake_get_pr_review_threads_includes_resolved_when_requested() -> None:
    """Test that resolved threads are included when include_resolved=True."""
    unresolved_thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=10,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )
    resolved_thread = PRReviewThread(
        id="PRRT_2",
        path="src/bar.py",
        line=20,
        is_resolved=True,
        is_outdated=False,
        comments=(),
    )

    github = FakeGitHub(pr_review_threads={123: [unresolved_thread, resolved_thread]})

    threads = github.get_pr_review_threads(Path("/repo"), 123, include_resolved=True)

    assert len(threads) == 2


def test_fake_get_pr_review_threads_sorts_by_path_and_line() -> None:
    """Test that threads are sorted by path, then by line."""
    thread_b_20 = PRReviewThread(
        id="PRRT_1",
        path="src/b.py",
        line=20,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )
    thread_a_10 = PRReviewThread(
        id="PRRT_2",
        path="src/a.py",
        line=10,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )
    thread_a_5 = PRReviewThread(
        id="PRRT_3",
        path="src/a.py",
        line=5,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )

    github = FakeGitHub(pr_review_threads={123: [thread_b_20, thread_a_10, thread_a_5]})

    threads = github.get_pr_review_threads(Path("/repo"), 123)

    assert len(threads) == 3
    assert threads[0].id == "PRRT_3"  # src/a.py:5
    assert threads[1].id == "PRRT_2"  # src/a.py:10
    assert threads[2].id == "PRRT_1"  # src/b.py:20


def test_fake_get_pr_review_threads_returns_empty_for_unknown_pr() -> None:
    """Test that unknown PR numbers return empty list."""
    github = FakeGitHub()

    threads = github.get_pr_review_threads(Path("/repo"), 999)

    assert threads == []


def test_fake_resolve_review_thread_tracks_resolution() -> None:
    """Test that resolve_review_thread tracks the resolved thread ID."""
    github = FakeGitHub()

    result = github.resolve_review_thread(Path("/repo"), "PRRT_1")

    assert result is True
    assert "PRRT_1" in github.resolved_thread_ids


def test_fake_resolve_review_thread_affects_subsequent_queries() -> None:
    """Test that resolving a thread affects subsequent get_pr_review_threads calls."""
    thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=42,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )

    github = FakeGitHub(pr_review_threads={123: [thread]})

    # Before resolution
    threads = github.get_pr_review_threads(Path("/repo"), 123)
    assert len(threads) == 1
    assert not threads[0].is_resolved

    # Resolve the thread
    github.resolve_review_thread(Path("/repo"), "PRRT_1")

    # After resolution - excluded by default
    threads = github.get_pr_review_threads(Path("/repo"), 123)
    assert len(threads) == 0

    # After resolution - included when requested, shows as resolved
    threads = github.get_pr_review_threads(Path("/repo"), 123, include_resolved=True)
    assert len(threads) == 1
    assert threads[0].is_resolved


def test_pr_review_comment_fields() -> None:
    """Test PRReviewComment dataclass fields."""
    comment = PRReviewComment(
        id=123,
        body="Fix this",
        author="reviewer",
        path="src/foo.py",
        line=42,
        created_at="2024-01-01T10:00:00Z",
    )

    assert comment.id == 123
    assert comment.body == "Fix this"
    assert comment.author == "reviewer"
    assert comment.path == "src/foo.py"
    assert comment.line == 42
    assert comment.created_at == "2024-01-01T10:00:00Z"


def test_pr_review_thread_with_none_line() -> None:
    """Test PRReviewThread with None line (file-level comment)."""
    thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=None,
        is_resolved=False,
        is_outdated=False,
        comments=(),
    )

    assert thread.line is None


def test_pr_review_thread_outdated_flag() -> None:
    """Test PRReviewThread is_outdated flag."""
    thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=42,
        is_resolved=False,
        is_outdated=True,
        comments=(),
    )

    assert thread.is_outdated is True


def test_fake_add_review_thread_reply_tracks_replies() -> None:
    """Test that add_review_thread_reply tracks the thread_id and body."""
    github = FakeGitHub()

    result = github.add_review_thread_reply(Path("/repo"), "PRRT_1", "Fixed this issue")

    assert result is True
    assert len(github.thread_replies) == 1
    assert github.thread_replies[0] == ("PRRT_1", "Fixed this issue")


def test_fake_add_review_thread_reply_multiple() -> None:
    """Test that multiple replies are tracked."""
    github = FakeGitHub()

    github.add_review_thread_reply(Path("/repo"), "PRRT_1", "First reply")
    github.add_review_thread_reply(Path("/repo"), "PRRT_2", "Second reply")

    assert len(github.thread_replies) == 2
    assert github.thread_replies[0] == ("PRRT_1", "First reply")
    assert github.thread_replies[1] == ("PRRT_2", "Second reply")
