"""Tests for learn command display functions."""

import pytest

from erk.cli.commands.learn.learn_cmd import LearnResult, _display_human_readable


def test_display_shows_remote_impl_message_when_set(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows remote implementation message when last_remote_impl_at is set."""
    result = LearnResult(
        issue_number=123,
        planning_session_id=None,
        implementation_session_ids=[],
        learn_session_ids=[],
        readable_session_ids=[],
        session_paths=[],
        local_session_ids=[],
        last_remote_impl_at="2024-01-16T14:30:00Z",
    )

    _display_human_readable(result)

    captured = capsys.readouterr()
    # user_output writes to stderr
    assert "(ran remotely - logs not accessible locally)" in captured.err


def test_display_shows_none_when_no_impl_at_all(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows (none) when no implementation happened."""
    result = LearnResult(
        issue_number=123,
        planning_session_id=None,
        implementation_session_ids=[],
        learn_session_ids=[],
        readable_session_ids=[],
        session_paths=[],
        local_session_ids=[],
        last_remote_impl_at=None,
    )

    _display_human_readable(result)

    captured = capsys.readouterr()
    assert "Implementation sessions:" in captured.err
    assert "(none)" in captured.err
    assert "(ran remotely" not in captured.err


def test_display_shows_impl_sessions_when_present(capsys: pytest.CaptureFixture[str]) -> None:
    """Display shows implementation sessions when they exist."""
    result = LearnResult(
        issue_number=123,
        planning_session_id=None,
        implementation_session_ids=["impl-session-abc"],
        learn_session_ids=[],
        readable_session_ids=[],
        session_paths=[],
        local_session_ids=[],
        last_remote_impl_at="2024-01-16T14:30:00Z",  # Even with remote, local takes precedence
    )

    _display_human_readable(result)

    captured = capsys.readouterr()
    assert "Implementation sessions (1):" in captured.err
    assert "impl-session-abc" in captured.err
    # Should NOT show remote message when local sessions exist
    assert "(ran remotely" not in captured.err
