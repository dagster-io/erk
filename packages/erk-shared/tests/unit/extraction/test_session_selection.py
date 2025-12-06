"""Tests for session selection logic."""

from pathlib import Path

from erk_shared.extraction.session_selection import auto_select_sessions
from erk_shared.extraction.types import BranchContext, SessionInfo


def make_session(
    session_id: str,
    size_bytes: int,
    is_current: bool = False,
) -> SessionInfo:
    """Helper to create a SessionInfo for testing."""
    return SessionInfo(
        session_id=session_id,
        path=Path(f"/test/{session_id}.jsonl"),
        size_bytes=size_bytes,
        mtime_unix=1000.0,
        is_current=is_current,
    )


class TestAutoSelectSessions:
    """Tests for auto_select_sessions function."""

    def test_on_trunk_returns_only_current_session(self) -> None:
        """When on trunk branch, only current session is returned."""
        sessions = [
            make_session("abc123", 5000, is_current=True),
            make_session("def456", 10000, is_current=False),
        ]
        branch_context = BranchContext(
            current_branch="main",
            trunk_branch="main",
            is_on_trunk=True,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id="abc123",
        )

        assert len(result) == 1
        assert result[0].session_id == "abc123"

    def test_on_trunk_no_current_session_returns_empty(self) -> None:
        """When on trunk with no current session, returns empty list."""
        sessions = [
            make_session("abc123", 5000, is_current=False),
            make_session("def456", 10000, is_current=False),
        ]
        branch_context = BranchContext(
            current_branch="main",
            trunk_branch="main",
            is_on_trunk=True,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id=None,
        )

        assert len(result) == 0

    def test_off_trunk_substantial_current_session_uses_it(self) -> None:
        """When off trunk with substantial current session, use only it."""
        sessions = [
            make_session("abc123", 5000, is_current=True),  # 5KB - substantial
            make_session("def456", 10000, is_current=False),
        ]
        branch_context = BranchContext(
            current_branch="feature-x",
            trunk_branch="main",
            is_on_trunk=False,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id="abc123",
            min_substantial_size=1024,
        )

        assert len(result) == 1
        assert result[0].session_id == "abc123"

    def test_off_trunk_trivial_current_selects_substantial_sessions(self) -> None:
        """When off trunk with trivial current, select substantial sessions."""
        sessions = [
            make_session("abc123", 500, is_current=True),  # 500B - trivial
            make_session("def456", 5000, is_current=False),  # 5KB - substantial
            make_session("ghi789", 8000, is_current=False),  # 8KB - substantial
        ]
        branch_context = BranchContext(
            current_branch="feature-x",
            trunk_branch="main",
            is_on_trunk=False,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id="abc123",
            min_substantial_size=1024,
        )

        assert len(result) == 2
        session_ids = {s.session_id for s in result}
        assert session_ids == {"def456", "ghi789"}

    def test_off_trunk_trivial_current_no_substantial_returns_current(self) -> None:
        """When off trunk with trivial current and no substantial, return current."""
        sessions = [
            make_session("abc123", 500, is_current=True),  # 500B - trivial
            make_session("def456", 700, is_current=False),  # 700B - also trivial
        ]
        branch_context = BranchContext(
            current_branch="feature-x",
            trunk_branch="main",
            is_on_trunk=False,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id="abc123",
            min_substantial_size=1024,
        )

        assert len(result) == 1
        assert result[0].session_id == "abc123"

    def test_off_trunk_no_current_session_returns_substantial(self) -> None:
        """When off trunk with no current session, return all substantial."""
        sessions = [
            make_session("abc123", 5000, is_current=False),
            make_session("def456", 10000, is_current=False),
            make_session("ghi789", 500, is_current=False),  # Too small
        ]
        branch_context = BranchContext(
            current_branch="feature-x",
            trunk_branch="main",
            is_on_trunk=False,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id=None,
            min_substantial_size=1024,
        )

        assert len(result) == 2
        session_ids = {s.session_id for s in result}
        assert session_ids == {"abc123", "def456"}

    def test_empty_sessions_returns_empty(self) -> None:
        """Empty session list returns empty result."""
        branch_context = BranchContext(
            current_branch="feature-x",
            trunk_branch="main",
            is_on_trunk=False,
        )

        result = auto_select_sessions(
            sessions=[],
            branch_context=branch_context,
            current_session_id=None,
        )

        assert len(result) == 0

    def test_custom_min_substantial_size(self) -> None:
        """Custom min_substantial_size is respected."""
        sessions = [
            make_session("abc123", 100, is_current=True),  # Trivial at 500 threshold
            make_session("def456", 600, is_current=False),  # Substantial at 500 threshold
        ]
        branch_context = BranchContext(
            current_branch="feature-x",
            trunk_branch="main",
            is_on_trunk=False,
        )

        result = auto_select_sessions(
            sessions=sessions,
            branch_context=branch_context,
            current_session_id="abc123",
            min_substantial_size=500,  # Custom threshold
        )

        # Current is trivial (100 < 500), so substantial sessions are selected
        assert len(result) == 1
        assert result[0].session_id == "def456"
