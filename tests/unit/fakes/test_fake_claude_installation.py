"""Tests for FakeClaudeInstallation.find_session_globally.

These tests verify that FakeClaudeInstallation correctly simulates global session lookup,
providing reliable test doubles for tests that use session functionality.
"""

from pathlib import Path

from erk_shared.learn.extraction.claude_installation.abc import FoundSession
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.non_ideal_state import SessionNotFound


def test_find_session_globally_finds_session_in_project() -> None:
    """Test find_session_globally returns session when it exists in a project."""
    project_path = Path("/project/path")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_path: FakeProject(
                sessions={
                    "session-123": FakeSessionData(
                        content="{}",
                        size_bytes=1024,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    result = installation.find_session_globally("session-123")

    assert isinstance(result, FoundSession)
    assert result.session.session_id == "session-123"
    assert result.session.size_bytes == 1024
    assert result.session.modified_at == 1000.0
    assert result.path == project_path / "session-123.jsonl"


def test_find_session_globally_returns_not_found_for_unknown_id() -> None:
    """Test find_session_globally returns SessionNotFound for unknown session ID."""
    installation = FakeClaudeInstallation.for_test(
        projects={
            Path("/project"): FakeProject(
                sessions={
                    "existing-session": FakeSessionData(
                        content="{}",
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    result = installation.find_session_globally("nonexistent-session")

    assert isinstance(result, SessionNotFound)
    assert result.session_id == "nonexistent-session"


def test_find_session_globally_searches_all_projects() -> None:
    """Test find_session_globally finds session across multiple projects."""
    project_a = Path("/project/a")
    project_b = Path("/project/b")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_a: FakeProject(
                sessions={
                    "session-a": FakeSessionData(
                        content="{}",
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            ),
            project_b: FakeProject(
                sessions={
                    "session-b": FakeSessionData(
                        content="{}",
                        size_bytes=200,
                        modified_at=2000.0,
                    )
                }
            ),
        }
    )

    # Find session in first project
    result_a = installation.find_session_globally("session-a")
    assert isinstance(result_a, FoundSession)
    assert result_a.session.session_id == "session-a"
    assert result_a.path == project_a / "session-a.jsonl"

    # Find session in second project
    result_b = installation.find_session_globally("session-b")
    assert isinstance(result_b, FoundSession)
    assert result_b.session.session_id == "session-b"
    assert result_b.path == project_b / "session-b.jsonl"


def test_find_session_globally_preserves_parent_session_id() -> None:
    """Test find_session_globally preserves parent_session_id for agent sessions."""
    project_path = Path("/project")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_path: FakeProject(
                sessions={
                    "agent-xyz": FakeSessionData(
                        content="{}",
                        size_bytes=500,
                        modified_at=1500.0,
                        parent_session_id="parent-session-id",
                    )
                }
            )
        }
    )

    result = installation.find_session_globally("agent-xyz")

    assert isinstance(result, FoundSession)
    assert result.session.session_id == "agent-xyz"
    assert result.session.parent_session_id == "parent-session-id"


def test_find_session_globally_with_no_projects() -> None:
    """Test find_session_globally returns SessionNotFound when no projects exist."""
    installation = FakeClaudeInstallation.for_test()

    result = installation.find_session_globally("any-session")

    assert isinstance(result, SessionNotFound)
    assert result.session_id == "any-session"


def test_find_session_globally_is_current_always_false() -> None:
    """Test find_session_globally always sets is_current to False."""
    installation = FakeClaudeInstallation.for_test(
        projects={
            Path("/project"): FakeProject(
                sessions={
                    "session-123": FakeSessionData(
                        content="{}",
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            )
        }
    )

    result = installation.find_session_globally("session-123")

    assert isinstance(result, FoundSession)
    assert result.session.is_current is False
