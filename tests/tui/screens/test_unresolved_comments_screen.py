"""Tests for _format_threads() in unresolved_comments_screen."""

from erk.tui.screens.unresolved_comments_screen import _format_threads
from erk_shared.gateway.github.types import PRReviewComment, PRReviewThread


def _make_comment(
    *,
    body: str = "Review comment body",
    author: str = "reviewer",
    path: str = "src/foo.py",
    line: int | None = 10,
    created_at: str = "2026-02-18T12:00:00Z",
) -> PRReviewComment:
    return PRReviewComment(
        id=1,
        body=body,
        author=author,
        path=path,
        line=line,
        created_at=created_at,
    )


def _make_thread(
    *,
    path: str = "src/foo.py",
    line: int | None = 10,
    comments: tuple[PRReviewComment, ...] = (),
) -> PRReviewThread:
    return PRReviewThread(
        id="PRRT_abc123",
        path=path,
        line=line,
        is_resolved=False,
        is_outdated=False,
        comments=comments,
    )


def test_empty_list_returns_no_comments_message() -> None:
    """Empty list returns italic 'No unresolved comments' message."""
    result = _format_threads([])
    assert result == "*No unresolved comments*"


def test_single_thread_with_one_comment() -> None:
    """Single thread formats with header, meta, and body."""
    comment = _make_comment(
        body="Please fix this",
        author="alice",
        path="src/main.py",
        line=42,
        created_at="2026-02-18T15:30:00Z",
    )
    thread = _make_thread(path="src/main.py", line=42, comments=(comment,))

    result = _format_threads([thread])

    assert "### `src/main.py:42`" in result
    assert "**alice** · 2026-02-18" in result
    assert "Please fix this" in result
    # No reply note for single comment
    assert "reply" not in result


def test_thread_with_no_line_number_omits_line_suffix() -> None:
    """Thread with line=None omits :line suffix in header."""
    comment = _make_comment(path="README.md", line=None)
    thread = _make_thread(path="README.md", line=None, comments=(comment,))

    result = _format_threads([thread])

    assert "### `README.md`" in result
    assert "README.md:" not in result


def test_thread_with_multiple_comments_shows_reply_count() -> None:
    """Thread with 3 comments shows '+ 2 replies' note."""
    comments = (
        _make_comment(body="Original comment", author="alice"),
        _make_comment(body="Reply 1", author="bob"),
        _make_comment(body="Reply 2", author="charlie"),
    )
    thread = _make_thread(comments=comments)

    result = _format_threads([thread])

    assert "*+ 2 replies*" in result


def test_thread_with_one_reply_shows_singular() -> None:
    """Thread with 2 comments shows '+ 1 reply' (singular)."""
    comments = (
        _make_comment(body="Original"),
        _make_comment(body="Reply"),
    )
    thread = _make_thread(comments=comments)

    result = _format_threads([thread])

    assert "*+ 1 reply*" in result
    assert "replies" not in result


def test_empty_thread_shows_empty_message() -> None:
    """Thread with no comments shows '(empty thread)' placeholder."""
    thread = _make_thread(comments=())

    result = _format_threads([thread])

    assert "*(empty thread)*" in result
