"""Tests for command palette registry."""

from erk.tui.commands.registry import get_all_commands, get_available_commands, get_display_name
from erk.tui.commands.types import CommandCategory, CommandContext
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
        assert isinstance(cmd.category, CommandCategory), f"Command {cmd.id} missing valid category"
        assert callable(cmd.is_available), f"Command {cmd.id} missing is_available"


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


def test_copy_checkout_available_when_worktree_branch_exists() -> None:
    """copy_checkout should be available when worktree_branch exists."""
    row = make_plan_row(123, "Test", worktree_branch="feature-123")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_checkout" in cmd_ids


def test_copy_checkout_not_available_when_worktree_branch_none() -> None:
    """copy_checkout should not be available when worktree_branch is None."""
    row = make_plan_row(123, "Test")  # worktree_branch defaults to None
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_checkout" not in cmd_ids


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


def test_prepare_commands_always_available() -> None:
    """Prepare commands should always be available."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_prepare" in cmd_ids
    assert "copy_prepare_dangerous" in cmd_ids
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


def test_fix_conflicts_remote_available_when_pr_exists() -> None:
    """fix_conflicts_remote should be available when PR number exists."""
    row = make_plan_row(123, "Test", pr_number=456)
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "fix_conflicts_remote" in cmd_ids


def test_fix_conflicts_remote_not_available_when_no_pr() -> None:
    """fix_conflicts_remote should not be available when no PR number."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "fix_conflicts_remote" not in cmd_ids


def test_copy_replan_available_when_issue_url_exists() -> None:
    """copy_replan should be available when issue URL exists."""
    row = make_plan_row(123, "Test", issue_url="https://github.com/test/repo/issues/123")
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "copy_replan" in cmd_ids


# === Dynamic Display Name Tests ===


def test_display_name_close_plan_shows_cli_command() -> None:
    """close_plan should show the CLI command with issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "close_plan")
    assert get_display_name(cmd, ctx) == "erk plan close 5831"


def test_display_name_submit_to_queue_shows_cli_command() -> None:
    """submit_to_queue should show the CLI command with issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "submit_to_queue")
    assert get_display_name(cmd, ctx) == "erk plan submit 5831"


def test_display_name_land_pr_shows_cli_command() -> None:
    """land_pr should show the CLI command with PR number."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "land_pr")
    assert get_display_name(cmd, ctx) == "erk land 456"


def test_display_name_fix_conflicts_remote_shows_cli_command() -> None:
    """fix_conflicts_remote should show the CLI command with PR number."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "fix_conflicts_remote")
    assert get_display_name(cmd, ctx) == "erk pr fix-conflicts-remote 456"


def test_display_name_open_issue_shows_labeled_url() -> None:
    """open_issue should show the labeled issue URL."""
    row = make_plan_row(
        5831,
        "Test Plan",
        issue_url="https://github.com/test/repo/issues/5831",
    )
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "open_issue")
    assert get_display_name(cmd, ctx) == "plan: https://github.com/test/repo/issues/5831"


def test_display_name_open_pr_shows_labeled_url() -> None:
    """open_pr should show the labeled PR URL."""
    row = make_plan_row(
        5831,
        "Test Plan",
        pr_url="https://github.com/test/repo/pull/456",
    )
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "open_pr")
    assert get_display_name(cmd, ctx) == "pr: https://github.com/test/repo/pull/456"


def test_display_name_open_run_shows_labeled_url() -> None:
    """open_run should show the labeled run URL."""
    row = make_plan_row(
        5831,
        "Test Plan",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "open_run")
    assert get_display_name(cmd, ctx) == "run: https://github.com/test/repo/actions/runs/789"


def test_display_name_copy_checkout_shows_branch() -> None:
    """copy_checkout should show the worktree branch."""
    row = make_plan_row(5831, "Test Plan", worktree_branch="feature-5831")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_checkout")
    assert get_display_name(cmd, ctx) == "erk br co feature-5831"


def test_display_name_copy_checkout_falls_back_to_pr() -> None:
    """copy_checkout should fall back to PR number if no worktree branch."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_checkout")
    assert get_display_name(cmd, ctx) == "erk pr co 456"


def test_display_name_copy_pr_checkout_shows_pr() -> None:
    """copy_pr_checkout should show the PR number in the full command."""
    row = make_plan_row(5831, "Test Plan", pr_number=456)
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_pr_checkout")
    expected = 'source "$(erk pr checkout 456 --script)" && erk pr sync --dangerous'
    assert get_display_name(cmd, ctx) == expected


def test_display_name_copy_prepare_shows_issue() -> None:
    """copy_prepare should show the issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_prepare")
    assert get_display_name(cmd, ctx) == "erk prepare 5831"


def test_display_name_copy_prepare_dangerous_shows_issue_and_flag() -> None:
    """copy_prepare_dangerous should show the issue number and --dangerous flag."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_prepare_dangerous")
    assert get_display_name(cmd, ctx) == "erk prepare 5831 --dangerous"


def test_display_name_copy_prepare_activate_shows_full_command() -> None:
    """copy_prepare_activate should show the full source && implement command."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_prepare_activate")
    expected = 'source "$(erk prepare 5831 --script)" && erk implement --dangerous'
    assert get_display_name(cmd, ctx) == expected


def test_display_name_copy_submit_shows_issue() -> None:
    """copy_submit should show the issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_submit")
    assert get_display_name(cmd, ctx) == "erk plan submit 5831"


def test_display_name_copy_replan_shows_issue() -> None:
    """copy_replan should show the issue number."""
    row = make_plan_row(5831, "Test Plan")
    ctx = CommandContext(row=row)
    cmd = next(c for c in get_all_commands() if c.id == "copy_replan")
    assert get_display_name(cmd, ctx) == "erk plan replan 5831"


def test_all_commands_have_get_display_name() -> None:
    """All commands should have get_display_name defined."""
    commands = get_all_commands()
    for cmd in commands:
        assert cmd.get_display_name is not None, f"Command {cmd.id} missing get_display_name"
