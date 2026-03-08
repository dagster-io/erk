"""Tests for NodeCommandProvider command discovery.

NodeCommandProvider now exposes all command categories (OPEN, COPY, and ACTION)
for the selected node's PR. These tests verify that the provider correctly
discovers and provides available commands.
"""

from erk.tui.commands.registry import get_available_commands
from erk.tui.commands.types import CommandContext
from erk.tui.views.types import ViewMode
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_provider_includes_action_commands() -> None:
    """NodeCommandProvider now exposes ACTION commands (no longer filtered)."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        pr_url="https://github.com/test/repo/pull/456",
        worktree_branch="feature-123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    all_cmd_ids = [cmd.id for cmd in get_available_commands(ctx)]

    # ACTION commands should be present
    assert "close_plan" in all_cmd_ids
    assert "dispatch_to_queue" in all_cmd_ids


def test_commands_include_open_commands() -> None:
    """Commands include OPEN category commands."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        pr_url="https://github.com/test/repo/pull/456",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    all_cmd_ids = [cmd.id for cmd in get_available_commands(ctx)]

    assert "open_issue" in all_cmd_ids
    assert "open_pr" in all_cmd_ids
    assert "open_run" in all_cmd_ids


def test_commands_include_copy_commands() -> None:
    """Commands include COPY category commands."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        worktree_branch="feature-123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    all_cmd_ids = [cmd.id for cmd in get_available_commands(ctx)]

    # At least one copy command should be available
    copy_cmds = [cid for cid in all_cmd_ids if cid.startswith("copy_")]
    assert len(copy_cmds) > 0, "Should have at least one COPY command"


def test_commands_exclude_pr_when_no_urls() -> None:
    """PR-specific OPEN commands excluded when row has no PR URL."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    all_cmd_ids = [cmd.id for cmd in get_available_commands(ctx)]

    assert "open_pr" not in all_cmd_ids
    assert "open_run" not in all_cmd_ids
