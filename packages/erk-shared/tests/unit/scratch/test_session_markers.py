"""Unit tests for session_markers module."""

from pathlib import Path

from erk_shared.scratch.session_markers import (
    create_plan_saved_issue_marker,
    create_plan_saved_marker,
    get_existing_saved_issue,
)

# create_plan_saved_marker tests


def test_create_plan_saved_marker_creates_file(tmp_path: Path) -> None:
    """Verify marker file is created at correct path."""
    session_id = "test-session-123"

    create_plan_saved_marker(session_id, tmp_path)

    marker_file = (
        tmp_path / ".erk" / "scratch" / "sessions" / session_id
        / "exit-plan-mode-hook.plan-saved.marker"
    )
    assert marker_file.exists()


def test_create_plan_saved_marker_has_descriptive_content(tmp_path: Path) -> None:
    """Verify marker file contains descriptive metadata."""
    session_id = "test-session-123"

    create_plan_saved_marker(session_id, tmp_path)

    marker_file = (
        tmp_path / ".erk" / "scratch" / "sessions" / session_id
        / "exit-plan-mode-hook.plan-saved.marker"
    )
    content = marker_file.read_text(encoding="utf-8")
    assert "Created by:" in content
    assert "Trigger:" in content
    assert "Effect:" in content
    assert "Lifecycle:" in content


# create_plan_saved_issue_marker tests


def test_create_plan_saved_issue_marker_stores_number(tmp_path: Path) -> None:
    """Verify issue number is stored as string."""
    session_id = "test-session-123"

    create_plan_saved_issue_marker(session_id, tmp_path, 42)

    marker_file = (
        tmp_path / ".erk" / "scratch" / "sessions" / session_id
        / "plan-saved-issue.marker"
    )
    assert marker_file.exists()
    assert marker_file.read_text(encoding="utf-8") == "42"


# get_existing_saved_issue tests


def test_get_existing_saved_issue_returns_issue_number(tmp_path: Path) -> None:
    """Verify stored issue number is returned."""
    session_id = "test-session-123"
    create_plan_saved_issue_marker(session_id, tmp_path, 99)

    result = get_existing_saved_issue(session_id, tmp_path)

    assert result == 99


def test_get_existing_saved_issue_returns_none_when_no_marker(tmp_path: Path) -> None:
    """Verify None is returned when no marker exists."""
    result = get_existing_saved_issue("nonexistent-session", tmp_path)

    assert result is None


def test_get_existing_saved_issue_returns_none_for_non_numeric(tmp_path: Path) -> None:
    """Verify None is returned when marker contains non-numeric content."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "plan-saved-issue.marker"
    marker_file.write_text("not-a-number", encoding="utf-8")

    result = get_existing_saved_issue(session_id, tmp_path)

    assert result is None


def test_marker_roundtrip(tmp_path: Path) -> None:
    """Verify create + get roundtrip works correctly."""
    session_id = "roundtrip-session"

    # Initially no marker
    assert get_existing_saved_issue(session_id, tmp_path) is None

    # Create marker
    create_plan_saved_issue_marker(session_id, tmp_path, 123)

    # Now returns the issue number
    assert get_existing_saved_issue(session_id, tmp_path) == 123
