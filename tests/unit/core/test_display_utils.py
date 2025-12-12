"""Unit tests for display_utils.py color formatting."""

from datetime import UTC, datetime

from erk.core.display_utils import (
    format_relative_time,
    format_submission_time,
    format_workflow_outcome,
    format_workflow_run_id,
    format_worktree_line,
    get_workflow_run_state,
)
from erk_shared.github.types import WorkflowRun


def test_pr_title_uses_cyan() -> None:
    """Test that PR titles render with cyan color."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = "#123"
    pr_title = "Add new feature"
    plan_summary = None

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Check for cyan ANSI escape code (36m)
    # ANSI cyan is \x1b[36m
    assert "\x1b[36m" in result, "Expected cyan color code for PR title"
    assert pr_title in result, "Expected PR title in output"


def test_plan_title_uses_bright_magenta() -> None:
    """Test that plan titles render with bright_magenta color."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = None
    pr_title = None
    plan_summary = "Implementation Plan for Feature"

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Check for bright magenta ANSI escape code (95m)
    # ANSI bright_magenta is \x1b[95m
    assert "\x1b[95m" in result, "Expected bright_magenta color code for plan title"
    assert plan_summary in result, "Expected plan summary in output"
    assert "📋" in result, "Expected plan emoji in output"


def test_pr_title_takes_precedence_over_plan() -> None:
    """Test color differentiation when both PR and plan exist (PR takes precedence)."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = "#123"
    pr_title = "Add new feature"
    plan_summary = "Implementation Plan for Feature"

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Should have cyan (PR title color), not bright_magenta (plan color)
    assert "\x1b[36m" in result, "Expected cyan for PR title"
    assert pr_title in result, "Expected PR title in output"
    # Plan summary should NOT appear when PR title exists
    assert plan_summary not in result, "Plan summary should not appear when PR title exists"
    # Should NOT have plan emoji when showing PR title
    assert "📋" not in result, "Plan emoji should not appear when PR title exists"


def test_no_plan_placeholder_uses_dimmed_white() -> None:
    """Test that [no plan] placeholder uses dimmed white color."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = None
    pr_title = None
    plan_summary = None

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Check for white color (37m) and dim (2m)
    # The ANSI codes appear as separate sequences: \x1b[37m\x1b[2m
    assert "\x1b[" in result, "Expected ANSI escape codes"
    assert "[no plan]" in result, "Expected [no plan] placeholder"
    # Check for dim modifier (can be separate or combined)
    assert "\x1b[2m" in result or "2;" in result or ";2m" in result, "Expected dim modifier"
    assert "37m" in result, "Expected white color code"


def test_format_workflow_run_id_with_url() -> None:
    """Test that workflow run ID with URL returns Rich markup for linkification."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="12345678",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc123",
    )
    workflow_url = "https://github.com/owner/repo/actions/runs/12345678"

    # Act
    result = format_workflow_run_id(workflow_run, workflow_url)

    # Assert: Check for Rich markup (used for proper rendering in Rich tables)
    assert "[cyan]" in result, "Expected Rich cyan markup"
    assert "[/cyan]" in result, "Expected Rich cyan close tag"
    assert "12345678" in result, "Expected run ID in output"
    assert f"[link={workflow_url}]" in result, "Expected Rich link markup"
    assert "[/link]" in result, "Expected Rich link close tag"


def test_format_workflow_run_id_without_url() -> None:
    """Test that workflow run ID without URL returns Rich markup without link."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="87654321",
        status="in_progress",
        conclusion=None,
        branch="feature",
        head_sha="def456",
    )
    workflow_url = None

    # Act
    result = format_workflow_run_id(workflow_run, workflow_url)

    # Assert: Check for Rich cyan markup but no link
    assert "[cyan]" in result, "Expected Rich cyan markup"
    assert "[/cyan]" in result, "Expected Rich cyan close tag"
    assert "87654321" in result, "Expected run ID in output"
    assert "[link=" not in result, "Should not have link markup without URL"


def test_format_workflow_run_id_none() -> None:
    """Test that None workflow run returns empty string."""
    # Act
    result = format_workflow_run_id(None, None)

    # Assert
    assert result == "", "Expected empty string for None workflow run"


def test_format_workflow_run_id_rich_table_rendering() -> None:
    """Test that workflow run ID output works correctly in Rich tables.

    The function uses Rich markup for proper rendering in Rich tables,
    with force_terminal=True on the Console to ensure hyperlinks render.
    """
    from io import StringIO

    from rich.console import Console
    from rich.table import Table

    # Arrange: Create workflow run with URL (triggers linkification)
    workflow_run = WorkflowRun(
        run_id="19652144787",  # Real-ish run ID length
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
    )
    workflow_url = "https://github.com/owner/repo/actions/runs/19652144787"

    run_id_cell = format_workflow_run_id(workflow_run, workflow_url)

    # Verify the markup is correct before rendering
    assert "19652144787" in run_id_cell, "Expected run ID in output"
    assert f"[link={workflow_url}]" in run_id_cell, "Expected Rich link markup"

    # Act: Render in a Rich table with force_terminal=True
    table = Table()
    table.add_column("Run ID", no_wrap=True)
    table.add_row(run_id_cell)

    buffer = StringIO()
    console = Console(file=buffer, width=120, force_terminal=True)
    console.print(table)
    output = buffer.getvalue()

    # Assert: Verify OSC 8 hyperlink was rendered
    assert "19652144787" in output, "Expected run ID in rendered output"
    assert "\x1b]8;" in output, "Expected OSC 8 escape sequence in rendered output"


def test_get_workflow_status_emoji_completed_success() -> None:
    """Test emoji for completed workflow with success conclusion."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="123",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "✅", "Expected green check for successful completion"


def test_get_workflow_status_emoji_completed_failure() -> None:
    """Test emoji for completed workflow with failure conclusion."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="456",
        status="completed",
        conclusion="failure",
        branch="main",
        head_sha="def",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "❌", "Expected red X for failed completion"


def test_get_workflow_status_emoji_completed_cancelled() -> None:
    """Test emoji for completed workflow with cancelled conclusion."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="789",
        status="completed",
        conclusion="cancelled",
        branch="main",
        head_sha="ghi",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "⛔", "Expected stop sign for cancelled workflow"


def test_get_workflow_status_emoji_in_progress() -> None:
    """Test emoji for in-progress workflow."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="101",
        status="in_progress",
        conclusion=None,
        branch="main",
        head_sha="jkl",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "⟳", "Expected reload symbol for in-progress workflow"


def test_get_workflow_status_emoji_queued() -> None:
    """Test emoji for queued workflow."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="202",
        status="queued",
        conclusion=None,
        branch="main",
        head_sha="mno",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "⧗", "Expected hourglass for queued workflow"


def test_get_workflow_status_emoji_unknown_status() -> None:
    """Test emoji for unknown workflow status."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="303",
        status="unknown_status",
        conclusion=None,
        branch="main",
        head_sha="pqr",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "❓", "Expected question mark for unknown status"


def test_format_workflow_status_with_url() -> None:
    """Test format_workflow_status with URL includes OSC 8 linkification."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="555",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="stu",
    )
    workflow_url = "https://github.com/owner/repo/actions/runs/555"

    # Act
    from erk.core.display_utils import format_workflow_status

    result = format_workflow_status(workflow_run, workflow_url)

    # Assert
    assert "✅" in result, "Expected success emoji"
    assert "CI" in result, "Expected CI text"
    assert "\x1b[36m" in result, "Expected cyan color"
    assert "\x1b]8;;" in result, "Expected OSC 8 link escape sequence"
    assert workflow_url in result, "Expected URL in OSC 8 link"


def test_format_workflow_status_without_url() -> None:
    """Test format_workflow_status without URL displays plain colored text."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="666",
        status="in_progress",
        conclusion=None,
        branch="main",
        head_sha="vwx",
    )
    workflow_url = None

    # Act
    from erk.core.display_utils import format_workflow_status

    result = format_workflow_status(workflow_run, workflow_url)

    # Assert
    assert "⟳" in result, "Expected in-progress emoji"
    assert "CI" in result, "Expected CI text"
    assert "\x1b[36m" in result, "Expected cyan color"
    assert "\x1b]8;;" not in result, "Should not have OSC 8 link without URL"


def test_format_workflow_status_none_workflow() -> None:
    """Test format_workflow_status with None workflow returns empty string."""
    # Act
    from erk.core.display_utils import format_workflow_status

    result = format_workflow_status(None, None)

    # Assert
    assert result == "", "Expected empty string for None workflow"


# Tests for get_workflow_run_state


def test_get_workflow_run_state_completed_success() -> None:
    """Test state for completed workflow with success conclusion."""
    workflow_run = WorkflowRun(
        run_id="123",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc",
    )
    result = get_workflow_run_state(workflow_run)
    assert result == "success"


def test_get_workflow_run_state_completed_failure() -> None:
    """Test state for completed workflow with failure conclusion."""
    workflow_run = WorkflowRun(
        run_id="456",
        status="completed",
        conclusion="failure",
        branch="main",
        head_sha="def",
    )
    result = get_workflow_run_state(workflow_run)
    assert result == "failure"


def test_get_workflow_run_state_completed_cancelled() -> None:
    """Test state for completed workflow with cancelled conclusion."""
    workflow_run = WorkflowRun(
        run_id="789",
        status="completed",
        conclusion="cancelled",
        branch="main",
        head_sha="ghi",
    )
    result = get_workflow_run_state(workflow_run)
    assert result == "cancelled"


def test_get_workflow_run_state_completed_other() -> None:
    """Test state for completed workflow with other conclusion maps to failure."""
    workflow_run = WorkflowRun(
        run_id="101",
        status="completed",
        conclusion="timed_out",
        branch="main",
        head_sha="jkl",
    )
    result = get_workflow_run_state(workflow_run)
    assert result == "failure"


def test_get_workflow_run_state_in_progress() -> None:
    """Test state for in-progress workflow."""
    workflow_run = WorkflowRun(
        run_id="202",
        status="in_progress",
        conclusion=None,
        branch="main",
        head_sha="mno",
    )
    result = get_workflow_run_state(workflow_run)
    assert result == "in_progress"


def test_get_workflow_run_state_queued() -> None:
    """Test state for queued workflow."""
    workflow_run = WorkflowRun(
        run_id="303",
        status="queued",
        conclusion=None,
        branch="main",
        head_sha="pqr",
    )
    result = get_workflow_run_state(workflow_run)
    assert result == "queued"


# Tests for format_workflow_outcome


def test_format_workflow_outcome_none() -> None:
    """Test outcome for None workflow returns dim dash."""
    result = format_workflow_outcome(None)
    assert result == "[dim]-[/dim]"


def test_format_workflow_outcome_queued() -> None:
    """Test outcome for queued workflow."""
    workflow_run = WorkflowRun(
        run_id="100",
        status="queued",
        conclusion=None,
        branch="main",
        head_sha="abc",
    )
    result = format_workflow_outcome(workflow_run)
    assert result == "[yellow]⧗ Queued[/yellow]"


def test_format_workflow_outcome_in_progress() -> None:
    """Test outcome for in-progress workflow."""
    workflow_run = WorkflowRun(
        run_id="200",
        status="in_progress",
        conclusion=None,
        branch="main",
        head_sha="def",
    )
    result = format_workflow_outcome(workflow_run)
    assert result == "[blue]⟳ Running[/blue]"


def test_format_workflow_outcome_success() -> None:
    """Test outcome for successful workflow."""
    workflow_run = WorkflowRun(
        run_id="300",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="ghi",
    )
    result = format_workflow_outcome(workflow_run)
    assert result == "[green]✅ Success[/green]"


def test_format_workflow_outcome_failure() -> None:
    """Test outcome for failed workflow."""
    workflow_run = WorkflowRun(
        run_id="400",
        status="completed",
        conclusion="failure",
        branch="main",
        head_sha="jkl",
    )
    result = format_workflow_outcome(workflow_run)
    assert result == "[red]❌ Failure[/red]"


def test_format_workflow_outcome_cancelled() -> None:
    """Test outcome for cancelled workflow."""
    workflow_run = WorkflowRun(
        run_id="500",
        status="completed",
        conclusion="cancelled",
        branch="main",
        head_sha="mno",
    )
    result = format_workflow_outcome(workflow_run)
    assert result == "[dim]⛔ Cancelled[/dim]"


# Tests for format_submission_time


def test_format_submission_time_none() -> None:
    """Test that None created_at returns dim dash."""
    result = format_submission_time(None)
    assert result == "[dim]-[/dim]"


def test_format_submission_time_utc_datetime() -> None:
    """Test formatting UTC datetime to local timezone."""
    # Create a known UTC timestamp
    utc_time = datetime(2024, 11, 26, 14, 30, 45, tzinfo=UTC)
    result = format_submission_time(utc_time)

    # Result should be MM-DD HH:MM format
    # The exact time depends on local timezone, but format should be consistent
    assert len(result) == 11, f"Expected 11 chars (MM-DD HH:MM), got: {result}"
    # Check it has the expected format structure
    assert result[2] == "-", f"Expected dash at position 2, got: {result}"
    assert result[5] == " ", f"Expected space at position 5, got: {result}"
    assert result[8] == ":", f"Expected colon at position 8, got: {result}"


def test_format_submission_time_preserves_date() -> None:
    """Test that the date part is correctly formatted."""
    # Use a timezone that's UTC+0 to verify the date parsing
    utc_time = datetime(2024, 12, 25, 10, 15, 0, tzinfo=UTC)
    result = format_submission_time(utc_time)

    # The result should contain "12-25" for December 25
    # (unless the local timezone shifts the date, which is correct behavior)
    # At minimum, verify the result is valid MM-DD HH:MM format
    parts = result.split(" ")
    assert len(parts) == 2, f"Expected date and time parts, got: {result}"
    date_part, time_part = parts
    assert len(date_part) == 5, f"Expected MM-DD format (5 chars), got: {date_part}"
    assert len(time_part) == 5, f"Expected HH:MM format (5 chars), got: {time_part}"


def test_format_submission_time_timezone_conversion() -> None:
    """Test that UTC time is converted to local timezone."""
    # Create a UTC timestamp at midnight
    utc_time = datetime(2024, 11, 26, 0, 0, 0, tzinfo=UTC)
    result = format_submission_time(utc_time)

    # Convert manually to compare
    expected_local = utc_time.astimezone()
    expected_result = expected_local.strftime("%m-%d %H:%M")

    assert result == expected_result, f"Expected {expected_result}, got {result}"


def test_format_submission_time_with_explicit_timezone() -> None:
    """Test that explicit timezone info is handled correctly."""
    # Create a timestamp with explicit UTC timezone
    explicit_time = datetime(2024, 7, 15, 18, 45, 30, tzinfo=UTC)
    result = format_submission_time(explicit_time)

    # Verify format
    assert len(result) == 11, f"Expected 11 chars, got: {result}"
    # The date should be July 15
    assert "07-15" in result or result.startswith("07-1"), f"Expected July date, got: {result}"


# Tests for format_relative_time


def test_format_relative_time_none() -> None:
    """Test that None timestamp returns empty string."""
    result = format_relative_time(None)
    assert result == ""


def test_format_relative_time_just_now() -> None:
    """Test that timestamps within 30 seconds show 'just now'."""
    now = datetime(2024, 11, 28, 10, 0, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "just now"


def test_format_relative_time_minutes() -> None:
    """Test that timestamps within an hour show minutes."""
    now = datetime(2024, 11, 28, 10, 30, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "30m ago"


def test_format_relative_time_hours() -> None:
    """Test that timestamps within a day show hours."""
    now = datetime(2024, 11, 28, 14, 0, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "4h ago"


def test_format_relative_time_days() -> None:
    """Test that timestamps within a week show days."""
    now = datetime(2024, 11, 30, 10, 0, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "2d ago"


def test_format_relative_time_weeks() -> None:
    """Test that timestamps within a month show weeks."""
    now = datetime(2024, 12, 14, 10, 0, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "2w ago"


def test_format_relative_time_months() -> None:
    """Test that timestamps within a year show months."""
    now = datetime(2025, 2, 28, 10, 0, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "3mo ago"


def test_format_relative_time_years() -> None:
    """Test that old timestamps show years."""
    now = datetime(2026, 11, 28, 10, 0, 0, tzinfo=UTC)
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "2y ago"


def test_format_relative_time_invalid_timestamp() -> None:
    """Test that invalid timestamp returns empty string."""
    result = format_relative_time("not-a-valid-timestamp")
    assert result == ""


def test_format_relative_time_timezone_aware() -> None:
    """Test that timestamps with different timezones work correctly."""
    now = datetime(2024, 11, 28, 12, 0, 0, tzinfo=UTC)
    # Timestamp that is effectively 2 hours ago in UTC
    timestamp = "2024-11-28T10:00:00+00:00"
    result = format_relative_time(timestamp, now=now)
    assert result == "2h ago"


# Tests for format_worktree_name_cell (from list_cmd.py)


def test_format_worktree_name_cell_exists_locally() -> None:
    """Test worktree that exists locally shows yellow name."""
    from erk.cli.commands.plan.list_cmd import format_worktree_name_cell

    result = format_worktree_name_cell("my-worktree", True)
    assert result == "[yellow]my-worktree[/yellow]"


def test_format_worktree_name_cell_not_exists_locally() -> None:
    """Test worktree that doesn't exist locally shows dash."""
    from erk.cli.commands.plan.list_cmd import format_worktree_name_cell

    result = format_worktree_name_cell("deleted-worktree", False)
    assert result == "-"


def test_format_worktree_name_cell_empty_name_not_exists() -> None:
    """Test that empty worktree name with exists_locally=False returns dash."""
    from erk.cli.commands.plan.list_cmd import format_worktree_name_cell

    result = format_worktree_name_cell("", False)
    assert result == "-"
