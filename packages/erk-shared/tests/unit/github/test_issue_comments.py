"""Unit tests for IssueComments wrapper class."""

import pytest

from erk_shared.gateway.github.issues.types import IssueComment, IssueComments
from erk_shared.non_ideal_state import EnsurableResult


def _make_comment(comment_id: int, body: str = "body") -> IssueComment:
    return IssueComment(
        body=body,
        url=f"https://github.com/owner/repo/issues/1#issuecomment-{comment_id}",
        id=comment_id,
        author="test-user",
    )


# ============================================================================
# EnsurableResult inheritance
# ============================================================================


def test_issue_comments_is_ensurable_result() -> None:
    """IssueComments is a subclass of EnsurableResult."""
    assert issubclass(IssueComments, EnsurableResult)


def test_issue_comments_ensure_returns_self() -> None:
    """IssueComments.ensure() returns self for one-liner unwrapping."""
    comments = IssueComments(comments=())
    assert comments.ensure() is comments


# ============================================================================
# __iter__
# ============================================================================


def test_issue_comments_iter_yields_items() -> None:
    """__iter__ yields each IssueComment in order."""
    c1 = _make_comment(1, "First")
    c2 = _make_comment(2, "Second")
    comments = IssueComments(comments=(c1, c2))
    assert list(comments) == [c1, c2]


def test_issue_comments_iter_empty() -> None:
    """__iter__ on empty collection yields no items."""
    comments = IssueComments(comments=())
    assert list(comments) == []


def test_issue_comments_iter_single() -> None:
    """__iter__ on single-item collection yields that item."""
    c = _make_comment(42)
    comments = IssueComments(comments=(c,))
    assert list(comments) == [c]


# ============================================================================
# Frozen dataclass
# ============================================================================


def test_issue_comments_is_frozen() -> None:
    """IssueComments is a frozen dataclass and cannot be mutated."""
    from dataclasses import FrozenInstanceError

    comments = IssueComments(comments=())
    with pytest.raises(FrozenInstanceError):
        comments.comments = ()  # type: ignore[misc]
