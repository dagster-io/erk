"""Tests for run command palette registry."""

from datetime import UTC, datetime

from erk.tui.commands.registry import (
    get_all_run_commands,
    get_available_run_commands,
    get_run_display_name,
)
from erk.tui.commands.types import CommandCategory, RunCommandContext
from erk.tui.data.types import RunRowData
from erk.tui.views.types import ViewMode
from tests.fakes.tests.tui_plan_data_provider import make_run_row


def test_all_run_commands_have_unique_ids() -> None:
    """All run commands should have unique IDs."""
    commands = get_all_run_commands()
    ids = [cmd.id for cmd in commands]
    assert len(ids) == len(set(ids)), "Run command IDs must be unique"


def test_all_run_commands_have_required_fields() -> None:
    """All run commands should have required fields populated."""
    commands = get_all_run_commands()
    for cmd in commands:
        assert cmd.id, f"Command missing id: {cmd}"
        assert cmd.name, f"Command {cmd.id} missing name"
        assert cmd.description, f"Command {cmd.id} missing description"
        assert isinstance(cmd.category, CommandCategory), f"Command {cmd.id} invalid category"
        assert callable(cmd.is_available), f"Command {cmd.id} missing is_available"


# === Cancel availability ===


def test_cancel_available_when_in_progress() -> None:
    """cancel_run should be available when run is in_progress."""
    row = make_run_row("123", status="in_progress", conclusion=None)
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "cancel_run" in cmd_ids


def test_cancel_available_when_queued() -> None:
    """cancel_run should be available when run is queued."""
    row = make_run_row("123", status="queued", conclusion=None)
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "cancel_run" in cmd_ids


def test_cancel_not_available_when_completed() -> None:
    """cancel_run should not be available when run is completed."""
    row = make_run_row("123", status="completed", conclusion="success")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "cancel_run" not in cmd_ids


# === Retry availability ===


def test_retry_available_when_failed() -> None:
    """retry_run should be available when run failed."""
    row = make_run_row("123", status="completed", conclusion="failure")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "retry_run" in cmd_ids
    assert "retry_failed_run" in cmd_ids


def test_retry_available_when_cancelled() -> None:
    """retry_run should be available when run was cancelled."""
    row = make_run_row("123", status="completed", conclusion="cancelled")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "retry_run" in cmd_ids


def test_retry_not_available_when_success() -> None:
    """retry_run should not be available when run succeeded."""
    row = make_run_row("123", status="completed", conclusion="success")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "retry_run" not in cmd_ids
    assert "retry_failed_run" not in cmd_ids


def test_retry_not_available_when_in_progress() -> None:
    """retry_run should not be available when run is still running."""
    row = make_run_row("123", status="in_progress", conclusion=None)
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "retry_run" not in cmd_ids


# === Open commands ===


def test_open_run_url_available_when_url_exists() -> None:
    """open_run_url should be available when run URL exists."""
    row = make_run_row("123", run_url="https://github.com/test/repo/actions/runs/123")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "open_run_url" in cmd_ids


def test_open_run_url_not_available_when_no_url() -> None:
    """open_run_url should not be available when no run URL."""
    row = RunRowData(
        run_id="123",
        run_url=None,
        status="completed",
        conclusion="success",
        status_display="Success",
        workflow_name="test",
        pr_number=None,
        pr_url=None,
        pr_display="-",
        pr_title=None,
        pr_state=None,
        title_display="-",
        branch_display="-",
        submitted_display="-",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        checks_display="-",
        run_id_display="123",
        branch="-",
    )
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "open_run_url" not in cmd_ids


def test_open_run_pr_available_when_pr_url_exists() -> None:
    """open_run_pr should be available when PR URL exists."""
    row = make_run_row("123", pr_url="https://github.com/test/repo/pull/456")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "open_run_pr" in cmd_ids


def test_open_run_pr_not_available_when_no_pr() -> None:
    """open_run_pr should not be available when no PR URL."""
    row = make_run_row("123", pr_url=None)
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    cmd_ids = [cmd.id for cmd in get_available_run_commands(ctx)]
    assert "open_run_pr" not in cmd_ids


# === Display names ===


def test_cancel_display_name() -> None:
    """cancel_run display name includes run ID."""
    row = make_run_row("99999")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    commands = get_all_run_commands()
    cancel_cmd = next(cmd for cmd in commands if cmd.id == "cancel_run")
    assert get_run_display_name(cancel_cmd, ctx) == "erk workflow run cancel 99999"


def test_retry_display_name() -> None:
    """retry_run display name includes run ID."""
    row = make_run_row("88888")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    commands = get_all_run_commands()
    retry_cmd = next(cmd for cmd in commands if cmd.id == "retry_run")
    assert get_run_display_name(retry_cmd, ctx) == "erk workflow run retry 88888"


def test_retry_failed_display_name() -> None:
    """retry_failed_run display name includes --failed flag."""
    row = make_run_row("77777")
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    commands = get_all_run_commands()
    cmd = next(c for c in commands if c.id == "retry_failed_run")
    assert get_run_display_name(cmd, ctx) == "erk workflow run retry 77777 --failed"
