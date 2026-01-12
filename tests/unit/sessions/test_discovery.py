"""Tests for session discovery functions.

These tests verify that get_readable_sessions correctly uses global session lookup.
"""

from pathlib import Path

from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.sessions.discovery import SessionsForPlan, get_readable_sessions


def test_get_readable_sessions_finds_global_sessions() -> None:
    """Test get_readable_sessions finds sessions via global lookup."""
    # Session exists in project_a, but we're looking globally
    project_a = Path("/project/a")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_a: FakeProject(
                sessions={
                    "planning-session": FakeSessionData(
                        content="{}",
                        size_bytes=1024,
                        modified_at=1000.0,
                    ),
                    "impl-session": FakeSessionData(
                        content="{}",
                        size_bytes=2048,
                        modified_at=2000.0,
                    ),
                }
            )
        }
    )

    sessions_for_plan = SessionsForPlan(
        planning_session_id="planning-session",
        implementation_session_ids=["impl-session"],
        learn_session_ids=[],
        last_remote_impl_at=None,
    )

    result = get_readable_sessions(sessions_for_plan, installation)

    assert len(result) == 2
    # Check first session
    assert result[0][0] == "planning-session"
    assert result[0][1] == project_a / "planning-session.jsonl"
    # Check second session
    assert result[1][0] == "impl-session"
    assert result[1][1] == project_a / "impl-session.jsonl"


def test_get_readable_sessions_returns_paths() -> None:
    """Test get_readable_sessions includes paths in return value."""
    project_path = Path("/project")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_path: FakeProject(
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

    sessions_for_plan = SessionsForPlan(
        planning_session_id="session-123",
        implementation_session_ids=[],
        learn_session_ids=[],
        last_remote_impl_at=None,
    )

    result = get_readable_sessions(sessions_for_plan, installation)

    assert len(result) == 1
    session_id, path = result[0]
    assert session_id == "session-123"
    assert path == project_path / "session-123.jsonl"


def test_get_readable_sessions_filters_missing_sessions() -> None:
    """Test get_readable_sessions excludes sessions that don't exist."""
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

    sessions_for_plan = SessionsForPlan(
        planning_session_id="existing-session",
        implementation_session_ids=["nonexistent-session"],
        learn_session_ids=["another-missing"],
        last_remote_impl_at=None,
    )

    result = get_readable_sessions(sessions_for_plan, installation)

    # Only the existing session should be returned
    assert len(result) == 1
    assert result[0][0] == "existing-session"


def test_get_readable_sessions_finds_sessions_across_projects() -> None:
    """Test get_readable_sessions finds sessions from different projects."""
    project_a = Path("/project/a")
    project_b = Path("/project/b")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_a: FakeProject(
                sessions={
                    "session-in-a": FakeSessionData(
                        content="{}",
                        size_bytes=100,
                        modified_at=1000.0,
                    )
                }
            ),
            project_b: FakeProject(
                sessions={
                    "session-in-b": FakeSessionData(
                        content="{}",
                        size_bytes=200,
                        modified_at=2000.0,
                    )
                }
            ),
        }
    )

    sessions_for_plan = SessionsForPlan(
        planning_session_id="session-in-a",
        implementation_session_ids=["session-in-b"],
        learn_session_ids=[],
        last_remote_impl_at=None,
    )

    result = get_readable_sessions(sessions_for_plan, installation)

    assert len(result) == 2
    session_ids = [sid for sid, _ in result]
    assert "session-in-a" in session_ids
    assert "session-in-b" in session_ids


def test_get_readable_sessions_empty_when_no_sessions_exist() -> None:
    """Test get_readable_sessions returns empty list when no sessions exist."""
    installation = FakeClaudeInstallation.for_test()

    sessions_for_plan = SessionsForPlan(
        planning_session_id="nonexistent",
        implementation_session_ids=["also-missing"],
        learn_session_ids=[],
        last_remote_impl_at=None,
    )

    result = get_readable_sessions(sessions_for_plan, installation)

    assert result == []


def test_get_readable_sessions_preserves_order() -> None:
    """Test get_readable_sessions preserves logical order from SessionsForPlan."""
    project_path = Path("/project")
    installation = FakeClaudeInstallation.for_test(
        projects={
            project_path: FakeProject(
                sessions={
                    "planning": FakeSessionData(
                        content="{}",
                        size_bytes=100,
                        modified_at=1000.0,
                    ),
                    "impl-1": FakeSessionData(
                        content="{}",
                        size_bytes=200,
                        modified_at=2000.0,
                    ),
                    "impl-2": FakeSessionData(
                        content="{}",
                        size_bytes=300,
                        modified_at=3000.0,
                    ),
                    "learn-1": FakeSessionData(
                        content="{}",
                        size_bytes=400,
                        modified_at=4000.0,
                    ),
                }
            )
        }
    )

    sessions_for_plan = SessionsForPlan(
        planning_session_id="planning",
        implementation_session_ids=["impl-1", "impl-2"],
        learn_session_ids=["learn-1"],
        last_remote_impl_at=None,
    )

    result = get_readable_sessions(sessions_for_plan, installation)

    session_ids = [sid for sid, _ in result]
    # Order should be: planning first, then impl, then learn
    assert session_ids == ["planning", "impl-1", "impl-2", "learn-1"]
