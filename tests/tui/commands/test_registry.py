"""Tests for command palette registry."""

from erk.tui.commands.registry import get_all_commands, get_available_commands
from erk.tui.commands.types import CommandContext
from tests.fakes.plan_data_provider import make_plan_row


def test_all_commands_have_unique_ids() -> None:
    """All commands should have unique IDs."""
    commands = get_all_commands()
    ids = [cmd.id for cmd in commands]
    assert len(ids) == len(set(ids)), "Command IDs must be unique"


def test_all_commands_have_required_fields() -> None:
    """All commands should have required fields populated."""
    commands = get_all_commands()
    for cmd in commands:
        assert cmd.id, f"Command missing id: {cmd}"
        assert cmd.name, f"Command {cmd.id} missing name"
        assert cmd.description, f"Command {cmd.id} missing description"
        assert callable(cmd.is_available), f"Command {cmd.id} missing is_available"


def test_open_browser_available_when_pr_url_exists() -> None:
    """open_browser should be available when PR URL exists."""
    row = make_plan_row(123, "Test", pr_url="https://github.com/test/repo/pull/456")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_browser" in cmd_ids


def test_open_browser_available_when_issue_url_exists() -> None:
    """open_browser should be available when issue URL exists."""
    row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_browser" in cmd_ids


def test_open_issue_available_when_issue_url_exists() -> None:
    """open_issue should be available when issue URL exists."""
    row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_issue" in cmd_ids


def test_open_pr_available_when_pr_url_exists() -> None:
    """open_pr should be available when PR URL exists."""
    row = make_plan_row(123, "Test", pr_url="https://github.com/test/repo/pull/456")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_pr" in cmd_ids


def test_open_pr_not_available_when_no_pr() -> None:
    """open_pr should not be available when no PR URL."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_pr" not in cmd_ids


def test_open_run_available_when_run_url_exists() -> None:
    """open_run should be available when run URL exists."""
    row = make_plan_row(123, "Test", run_url="https://github.com/test/repo/actions/runs/789")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_run" in cmd_ids


def test_open_run_not_available_when_no_run() -> None:
    """open_run should not be available when no run URL."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "open_run" not in cmd_ids


def test_copy_checkout_always_available() -> None:
    """copy_checkout should always be available."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_checkout" in cmd_ids


def test_copy_pr_checkout_available_when_pr_exists() -> None:
    """copy_pr_checkout should be available when PR number exists."""
    row = make_plan_row(123, "Test", pr_number=456)
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_pr_checkout" in cmd_ids


def test_copy_pr_checkout_not_available_when_no_pr() -> None:
    """copy_pr_checkout should not be available when no PR number."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_pr_checkout" not in cmd_ids


def test_implement_commands_always_available() -> None:
    """Implement commands should always be available."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_implement" in cmd_ids
    assert "copy_implement_dangerous" in cmd_ids
    assert "copy_implement_yolo" in cmd_ids
    assert "copy_submit" in cmd_ids


def test_close_plan_always_available() -> None:
    """close_plan should always be available."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "close_plan" in cmd_ids


def test_close_plan_has_no_shortcut() -> None:
    """close_plan should have no keyboard shortcut (must use palette)."""
    commands = get_all_commands()
    close_plan = next(cmd for cmd in commands if cmd.id == "close_plan")
    assert close_plan.shortcut is None


def test_land_pr_available_when_all_conditions_met() -> None:
    """land_pr should be available when PR is open and remote run exists."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="OPEN",
        exists_locally=True,
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" in cmd_ids


def test_land_pr_not_available_when_no_pr() -> None:
    """land_pr should not be available when no PR."""
    row = make_plan_row(123, "Test", run_url="https://github.com/test/repo/actions/runs/789")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" not in cmd_ids


def test_land_pr_not_available_when_pr_merged() -> None:
    """land_pr should not be available when PR is already merged."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="MERGED",
        exists_locally=False,
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" not in cmd_ids


def test_land_pr_available_when_exists_locally() -> None:
    """land_pr should be available even when worktree exists locally."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="OPEN",
        exists_locally=True,
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" in cmd_ids


def test_land_pr_not_available_when_no_run() -> None:
    """land_pr should not be available when no remote run."""
    row = make_plan_row(
        123,
        "Test",
        pr_number=456,
        pr_state="OPEN",
        exists_locally=False,
    )
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" not in cmd_ids
