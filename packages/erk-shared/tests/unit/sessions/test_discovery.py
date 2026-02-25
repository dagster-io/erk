"""Tests for session discovery functions."""

from erk_shared.sessions.discovery import SessionsForPlan


def test_sessions_for_plan_all_session_ids_empty() -> None:
    """All session IDs returns empty for empty object."""
    sessions = SessionsForPlan(
        planning_session_id=None,
        implementation_session_ids=[],
        learn_session_ids=[],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        last_session_gist_url=None,
        last_session_id=None,
        last_session_source=None,
    )
    assert sessions.all_session_ids() == []


def test_sessions_for_plan_all_session_ids_planning_only() -> None:
    """All session IDs includes planning session first."""
    sessions = SessionsForPlan(
        planning_session_id="planning-123",
        implementation_session_ids=[],
        learn_session_ids=[],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        last_session_gist_url=None,
        last_session_id=None,
        last_session_source=None,
    )
    assert sessions.all_session_ids() == ["planning-123"]


def test_sessions_for_plan_all_session_ids_deduplicates() -> None:
    """All session IDs deduplicates across categories."""
    sessions = SessionsForPlan(
        planning_session_id="shared-session",
        implementation_session_ids=["shared-session", "impl-only"],
        learn_session_ids=["learn-only", "shared-session"],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        last_session_gist_url=None,
        last_session_id=None,
        last_session_source=None,
    )
    # shared-session should only appear once (from planning)
    result = sessions.all_session_ids()
    assert result == ["shared-session", "impl-only", "learn-only"]


def test_sessions_for_plan_all_session_ids_order() -> None:
    """All session IDs returns in logical order: planning, impl, learn."""
    sessions = SessionsForPlan(
        planning_session_id="plan-session",
        implementation_session_ids=["impl-1", "impl-2"],
        learn_session_ids=["learn-1"],
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        last_session_gist_url=None,
        last_session_id=None,
        last_session_source=None,
    )
    result = sessions.all_session_ids()
    assert result == ["plan-session", "impl-1", "impl-2", "learn-1"]
