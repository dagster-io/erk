"""Unit tests for session_markers module."""

from pathlib import Path

from erk_shared.scratch.session_markers import (
    create_plan_saved_branch_marker,
    create_plan_saved_marker,
    create_plan_saved_pr_marker,
    get_existing_saved_branch,
    get_existing_saved_pr,
    read_plan_saved_marker,
    read_roadmap_step_marker,
)

# create_plan_saved_marker tests


def test_create_plan_saved_marker_creates_file(tmp_path: Path) -> None:
    """Verify marker file is created at correct path."""
    session_id = "test-session-123"

    create_plan_saved_marker(session_id, tmp_path, 42)

    marker_file = (
        tmp_path
        / ".erk"
        / "scratch"
        / "sessions"
        / session_id
        / "exit-plan-mode-hook.plan-saved.marker"
    )
    assert marker_file.exists()


def test_create_plan_saved_marker_has_descriptive_content(tmp_path: Path) -> None:
    """Verify marker file contains plan number and descriptive metadata."""
    session_id = "test-session-123"

    create_plan_saved_marker(session_id, tmp_path, 42)

    marker_file = (
        tmp_path
        / ".erk"
        / "scratch"
        / "sessions"
        / session_id
        / "exit-plan-mode-hook.plan-saved.marker"
    )
    content = marker_file.read_text(encoding="utf-8")
    assert content.startswith("42\n")
    assert "Created by:" in content
    assert "Trigger:" in content
    assert "Effect:" in content
    assert "Lifecycle:" in content


# read_plan_saved_marker tests


def test_read_plan_saved_marker_returns_plan_number(tmp_path: Path) -> None:
    """Verify plan number is returned from marker."""
    session_id = "test-session-123"
    create_plan_saved_marker(session_id, tmp_path, 99)

    result = read_plan_saved_marker(session_id, tmp_path)

    assert result == 99


def test_read_plan_saved_marker_returns_none_when_no_marker(tmp_path: Path) -> None:
    """Verify None is returned when no marker exists."""
    result = read_plan_saved_marker("nonexistent-session", tmp_path)

    assert result is None


def test_read_plan_saved_marker_returns_none_for_non_numeric(tmp_path: Path) -> None:
    """Verify None is returned when first line is not numeric."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
    marker_file.write_text("not-a-number\n", encoding="utf-8")

    result = read_plan_saved_marker(session_id, tmp_path)

    assert result is None


# create_plan_saved_pr_marker tests


def test_create_plan_saved_pr_marker_stores_number_and_title(tmp_path: Path) -> None:
    """Verify PR number and title are stored."""
    session_id = "test-session-123"

    create_plan_saved_pr_marker(session_id, tmp_path, 42, title="My Plan")

    marker_file = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "plan-saved.marker"
    assert marker_file.exists()
    assert marker_file.read_text(encoding="utf-8") == "42\nMy Plan"


# get_existing_saved_pr tests


def test_get_existing_saved_pr_returns_plan_number_for_same_title(tmp_path: Path) -> None:
    """Verify stored plan number is returned when titles match."""
    session_id = "test-session-123"
    create_plan_saved_pr_marker(session_id, tmp_path, 99, title="My Plan")

    result = get_existing_saved_pr(session_id, tmp_path, title="My Plan")

    assert result == 99


def test_get_existing_saved_pr_returns_none_for_different_title(tmp_path: Path) -> None:
    """Verify None is returned when titles differ (distinct plans allowed)."""
    session_id = "test-session-123"
    create_plan_saved_pr_marker(session_id, tmp_path, 99, title="First Plan")

    result = get_existing_saved_pr(session_id, tmp_path, title="Second Plan")

    assert result is None


def test_get_existing_saved_pr_returns_none_when_no_marker(tmp_path: Path) -> None:
    """Verify None is returned when no marker exists."""
    result = get_existing_saved_pr("nonexistent-session", tmp_path, title="Any Title")

    assert result is None


def test_get_existing_saved_pr_returns_none_for_non_numeric(tmp_path: Path) -> None:
    """Verify None is returned when marker contains non-numeric content."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "plan-saved.marker"
    marker_file.write_text("not-a-number", encoding="utf-8")

    result = get_existing_saved_pr(session_id, tmp_path, title="Any Title")

    assert result is None


def test_get_existing_saved_pr_old_format_backwards_compat(tmp_path: Path) -> None:
    """Old-format marker (no title line) treats as match for backwards compat."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "plan-saved.marker"
    marker_file.write_text("42", encoding="utf-8")

    result = get_existing_saved_pr(session_id, tmp_path, title="Any Title")

    assert result == 42


# create_plan_saved_branch_marker tests


def test_create_plan_saved_branch_marker_stores_branch(tmp_path: Path) -> None:
    """Verify branch name is stored correctly."""
    session_id = "test-session-123"

    create_plan_saved_branch_marker(session_id, tmp_path, "plnd/my-feature-02-22-1234")

    marker_file = (
        tmp_path / ".erk" / "scratch" / "sessions" / session_id / "plan-saved-branch.marker"
    )
    assert marker_file.exists()
    assert marker_file.read_text(encoding="utf-8") == "plnd/my-feature-02-22-1234"


# get_existing_saved_branch tests


def test_get_existing_saved_branch_returns_branch_name(tmp_path: Path) -> None:
    """Verify stored branch name is returned."""
    session_id = "test-session-123"
    create_plan_saved_branch_marker(session_id, tmp_path, "plnd/feature-branch-01-01-0000")

    result = get_existing_saved_branch(session_id, tmp_path)

    assert result == "plnd/feature-branch-01-01-0000"


def test_get_existing_saved_branch_returns_none_when_no_marker(tmp_path: Path) -> None:
    """Verify None is returned when no marker exists."""
    result = get_existing_saved_branch("nonexistent-session", tmp_path)

    assert result is None


def test_get_existing_saved_branch_returns_none_for_empty_content(tmp_path: Path) -> None:
    """Verify None is returned when marker contains empty content."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "plan-saved-branch.marker"
    marker_file.write_text("", encoding="utf-8")

    result = get_existing_saved_branch(session_id, tmp_path)

    assert result is None


def test_branch_marker_roundtrip(tmp_path: Path) -> None:
    """Verify create + get roundtrip works correctly for branch markers."""
    session_id = "roundtrip-session"

    # Initially no marker
    assert get_existing_saved_branch(session_id, tmp_path) is None

    # Create marker
    create_plan_saved_branch_marker(session_id, tmp_path, "plnd/roundtrip-02-22-1234")

    # Now returns the branch name
    assert get_existing_saved_branch(session_id, tmp_path) == "plnd/roundtrip-02-22-1234"


# read_roadmap_step_marker tests


def test_read_roadmap_step_marker_returns_node_id(tmp_path: Path) -> None:
    """Verify stored node ID is returned."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "roadmap-step.marker"
    marker_file.write_text("phase1.step2", encoding="utf-8")

    result = read_roadmap_step_marker(session_id, tmp_path)

    assert result == "phase1.step2"


def test_read_roadmap_step_marker_returns_none_when_no_marker(tmp_path: Path) -> None:
    """Verify None is returned when no marker exists."""
    result = read_roadmap_step_marker("nonexistent-session", tmp_path)

    assert result is None


def test_read_roadmap_step_marker_returns_none_for_empty_content(tmp_path: Path) -> None:
    """Verify None is returned when marker contains empty content."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "roadmap-step.marker"
    marker_file.write_text("", encoding="utf-8")

    result = read_roadmap_step_marker(session_id, tmp_path)

    assert result is None


def test_read_roadmap_step_marker_strips_whitespace(tmp_path: Path) -> None:
    """Verify whitespace is stripped from marker content."""
    session_id = "test-session-123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    marker_file = marker_dir / "roadmap-step.marker"
    marker_file.write_text("  phase1.step2  \n", encoding="utf-8")

    result = read_roadmap_step_marker(session_id, tmp_path)

    assert result == "phase1.step2"


def test_marker_roundtrip(tmp_path: Path) -> None:
    """Verify create + get roundtrip works correctly."""
    session_id = "roundtrip-session"
    title = "Roundtrip Plan"

    # Initially no marker
    assert get_existing_saved_pr(session_id, tmp_path, title=title) is None

    # Create marker
    create_plan_saved_pr_marker(session_id, tmp_path, 123, title=title)

    # Now returns the PR number for same title
    assert get_existing_saved_pr(session_id, tmp_path, title=title) == 123

    # Different title returns None
    assert get_existing_saved_pr(session_id, tmp_path, title="Different Plan") is None
