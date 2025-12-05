"""Tests for FakeClaudeSessionDetector.

Tests that verify the fake implementation correctly tracks session detection calls
and returns configured responses for testing.
"""

from pathlib import Path

from erk_shared.integrations.claude.fake import FakeClaudeSessionDetector


def test_fake_claude_session_detector_no_active_sessions_by_default() -> None:
    """Test that FakeClaudeSessionDetector returns False when no sessions configured."""
    fake = FakeClaudeSessionDetector()

    result = fake.has_active_session(Path("/some/worktree"))

    assert result is False


def test_fake_claude_session_detector_returns_true_for_configured_session() -> None:
    """Test that FakeClaudeSessionDetector returns True for configured session paths."""
    active_path = Path("/test/worktree")
    fake = FakeClaudeSessionDetector(active_sessions={active_path})

    result = fake.has_active_session(active_path)

    assert result is True


def test_fake_claude_session_detector_returns_false_for_non_configured_path() -> None:
    """Test that FakeClaudeSessionDetector returns False for non-configured paths."""
    active_path = Path("/test/worktree1")
    other_path = Path("/test/worktree2")
    fake = FakeClaudeSessionDetector(active_sessions={active_path})

    result = fake.has_active_session(other_path)

    assert result is False


def test_fake_claude_session_detector_tracks_check_calls() -> None:
    """Test that FakeClaudeSessionDetector tracks all check calls."""
    fake = FakeClaudeSessionDetector()

    path1 = Path("/test/path1")
    path2 = Path("/test/path2")

    fake.has_active_session(path1)
    fake.has_active_session(path2)
    fake.has_active_session(path1)

    assert fake.check_calls == [path1, path2, path1]


def test_fake_claude_session_detector_multiple_active_sessions() -> None:
    """Test that FakeClaudeSessionDetector handles multiple active session paths."""
    path1 = Path("/test/worktree1")
    path2 = Path("/test/worktree2")
    path3 = Path("/test/worktree3")
    fake = FakeClaudeSessionDetector(active_sessions={path1, path2})

    assert fake.has_active_session(path1) is True
    assert fake.has_active_session(path2) is True
    assert fake.has_active_session(path3) is False
