"""Tests for NodeCommandProvider filtering logic.

NodeCommandProvider only allows OPEN and COPY commands, excluding ACTION
commands that require the full app context. These tests verify the filtering
at the registry level since the provider delegates to get_available_commands
and filters by category.
"""

from erk.tui.commands.registry import get_available_commands
from erk.tui.commands.types import CommandCategory, CommandContext
from erk.tui.views.types import ViewMode
from erk_shared.gateway.plan_data_provider.fake import make_plan_row

_ALLOWED_CATEGORIES = {CommandCategory.OPEN, CommandCategory.COPY}


def _get_filtered_commands(ctx: CommandContext) -> list[str]:
    """Get command IDs after applying NodeCommandProvider's category filter."""
    return [cmd.id for cmd in get_available_commands(ctx) if cmd.category in _ALLOWED_CATEGORIES]


def _get_excluded_commands(ctx: CommandContext) -> list[str]:
    """Get command IDs that would be excluded by NodeCommandProvider."""
    return [
        cmd.id for cmd in get_available_commands(ctx) if cmd.category not in _ALLOWED_CATEGORIES
    ]


def test_filtered_commands_exclude_action_category() -> None:
    """NodeCommandProvider filter excludes all ACTION commands."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        pr_url="https://github.com/test/repo/pull/456",
        worktree_branch="feature-123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    filtered = _get_filtered_commands(ctx)
    excluded = _get_excluded_commands(ctx)

    # ACTION commands exist but are excluded
    assert len(excluded) > 0, "Should have ACTION commands to exclude"
    for cmd_id in excluded:
        assert cmd_id not in filtered


def test_filtered_commands_include_open_commands() -> None:
    """NodeCommandProvider filter includes OPEN commands."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        pr_url="https://github.com/test/repo/pull/456",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    filtered = _get_filtered_commands(ctx)

    assert "open_issue" in filtered
    assert "open_pr" in filtered
    assert "open_run" in filtered


def test_filtered_commands_include_copy_commands() -> None:
    """NodeCommandProvider filter includes COPY commands."""
    row = make_plan_row(
        123,
        "Test",
        plan_url="https://github.com/test/repo/issues/123",
        worktree_branch="feature-123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    filtered = _get_filtered_commands(ctx)

    # At least one copy command should be available
    copy_cmds = [cid for cid in filtered if cid.startswith("copy_")]
    assert len(copy_cmds) > 0, "Should have at least one COPY command"


def test_filtered_commands_empty_when_no_urls() -> None:
    """No OPEN commands when row has no URLs beyond plan_url."""
    row = make_plan_row(123, "Test")
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    filtered = _get_filtered_commands(ctx)

    assert "open_pr" not in filtered
    assert "open_run" not in filtered
