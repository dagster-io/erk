"""Tests for RunCommandProvider integration layer.

The RunCommandProvider delegates to get_available_run_commands() and
get_run_display_name() from the registry. These tests verify the
Provider-level integration: that discover yields the right commands
and search filters them correctly.

Since Textual Provider instances require full app context and are
not directly accessible, we test the underlying logic that the
Provider calls: get_available_run_commands with RunCommandContext.
"""

from erk.tui.commands.registry import get_available_run_commands, get_run_display_name
from erk.tui.commands.types import RunCommandContext
from erk.tui.views.types import ViewMode
from tests.fakes.tests.tui_plan_data_provider import make_run_row


def test_run_command_provider_discover_yields_available_commands() -> None:
    """With a failed run selected, available commands include retry and open."""
    row = make_run_row(
        "999",
        status="completed",
        conclusion="failure",
        run_url="https://github.com/test/repo/actions/runs/999",
    )
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    commands = get_available_run_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]

    # A failed run should have retry, open, and copy commands
    assert "retry_run" in cmd_ids
    assert "retry_failed_run" in cmd_ids
    assert "open_run_url" in cmd_ids
    assert "copy_retry_cmd" in cmd_ids


def test_run_command_provider_search_filters_by_query() -> None:
    """Search-equivalent: display names contain text for fuzzy matching."""
    row = make_run_row(
        "888",
        status="completed",
        conclusion="failure",
        run_url="https://github.com/test/repo/actions/runs/888",
        pr_url="https://github.com/test/repo/pull/42",
    )
    ctx = RunCommandContext(row=row, view_mode=ViewMode.RUNS)
    commands = get_available_run_commands(ctx)

    # Build search text the same way the Provider does: "description: display_name"
    search_texts = [
        f"{cmd.description}: {get_run_display_name(cmd, ctx)}" for cmd in commands
    ]

    # "retry" should match only retry-related commands (subset of all)
    retry_matches = [t for t in search_texts if "retry" in t.lower()]
    assert len(retry_matches) > 0, "Should find at least one retry-related command"
    assert len(retry_matches) < len(search_texts), (
        "Retry matches should be a subset of all commands"
    )
