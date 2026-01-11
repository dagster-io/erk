"""Tests for impl_events extraction functions."""

from erk_shared.github.metadata.core import render_metadata_block
from erk_shared.github.metadata.types import MetadataBlock
from erk_shared.learn.impl_events import (
    extract_implementation_sessions,
    extract_learn_sessions,
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


def test_extract_implementation_sessions_empty() -> None:
    """Extract from empty comments list returns empty list."""
    result = extract_implementation_sessions([])
    assert result == []


def test_extract_implementation_sessions_no_blocks() -> None:
    """Extract from comments without impl blocks returns empty list."""
    comments = ["Regular comment", "Another comment"]
    result = extract_implementation_sessions(comments)
    assert result == []


def test_extract_implementation_sessions_started_only() -> None:
    """Extract session from impl-started block."""
    comment = _make_impl_comment("started", "abc123")
    result = extract_implementation_sessions([comment])
    assert result == ["abc123"]


def test_extract_implementation_sessions_ended_only() -> None:
    """Extract session from impl-ended block."""
    comment = _make_impl_comment("ended", "def456")
    result = extract_implementation_sessions([comment])
    assert result == ["def456"]


def test_extract_implementation_sessions_multiple_comments() -> None:
    """Extract sessions from multiple comments."""
    comments = [
        _make_impl_comment("started", "session1"),
        _make_impl_comment("ended", "session1"),  # Same session
        _make_impl_comment("started", "session2"),
    ]
    result = extract_implementation_sessions(comments)
    # Should deduplicate session1
    assert result == ["session1", "session2"]


def test_extract_implementation_sessions_preserves_order() -> None:
    """Sessions returned in order of first occurrence."""
    comments = [
        _make_impl_comment("started", "third"),
        _make_impl_comment("started", "first"),
        _make_impl_comment("started", "second"),
    ]
    # Order is based on iteration order - comment 1 processed first
    result = extract_implementation_sessions(comments)
    assert result == ["third", "first", "second"]


def test_extract_learn_sessions_empty() -> None:
    """Extract from empty comments list returns empty list."""
    result = extract_learn_sessions([])
    assert result == []


def test_extract_learn_sessions_no_blocks() -> None:
    """Extract from comments without learn blocks returns empty list."""
    comments = ["Regular comment", _make_impl_comment("started", "abc")]
    result = extract_learn_sessions(comments)
    assert result == []


def test_extract_learn_sessions_single() -> None:
    """Extract session from single learn comment."""
    comment = _make_learn_comment("learn-session-1")
    result = extract_learn_sessions([comment])
    assert result == ["learn-session-1"]


def test_extract_learn_sessions_multiple() -> None:
    """Extract sessions from multiple learn comments."""
    comments = [
        _make_learn_comment("session-a"),
        _make_learn_comment("session-b"),
        _make_learn_comment("session-a"),  # Duplicate
    ]
    result = extract_learn_sessions(comments)
    # Should deduplicate
    assert result == ["session-a", "session-b"]


def test_extract_learn_sessions_mixed_comments() -> None:
    """Learn extraction ignores impl blocks."""
    comments = [
        _make_impl_comment("started", "impl-session"),
        _make_learn_comment("learn-session"),
        "Plain text comment",
    ]
    result = extract_learn_sessions(comments)
    assert result == ["learn-session"]
