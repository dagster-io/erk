"""Tests for the LaunchScreen modal."""

from erk.tui.commands.registry import get_all_commands
from erk.tui.commands.types import CommandCategory, CommandContext
from erk.tui.screens.launch_screen import LaunchScreen
from erk.tui.views.types import ViewMode
from tests.fakes.gateway.plan_data_provider import make_plan_row


def test_launch_key_only_set_on_action_commands() -> None:
    """launch_key should only be set on ACTION category commands."""
    all_commands = get_all_commands()
    for cmd in all_commands:
        if cmd.launch_key is not None:
            assert cmd.category == CommandCategory.ACTION, (
                f"Command {cmd.id} has launch_key={cmd.launch_key!r} but is {cmd.category.name}"
            )


def test_launch_key_no_duplicate_keys_within_plan_view() -> None:
    """Plan action launch_keys should not have duplicate key bindings."""
    all_commands = get_all_commands()
    plan_action_keys = [
        cmd.launch_key
        for cmd in all_commands
        if cmd.category == CommandCategory.ACTION
        and cmd.launch_key is not None
        and cmd.id not in {"close_objective", "one_shot_plan", "check_objective"}
    ]
    assert len(plan_action_keys) == len(set(plan_action_keys)), (
        f"Duplicate launch_keys in plan actions: {plan_action_keys}"
    )


def test_launch_key_no_duplicate_keys_within_objective_view() -> None:
    """Objective action launch_keys should not have duplicate key bindings."""
    all_commands = get_all_commands()
    obj_action_keys = [
        cmd.launch_key
        for cmd in all_commands
        if cmd.category == CommandCategory.ACTION
        and cmd.launch_key is not None
        and cmd.id in {"close_objective", "one_shot_plan", "check_objective"}
    ]
    assert len(obj_action_keys) == len(set(obj_action_keys)), (
        f"Duplicate launch_keys in objective actions: {obj_action_keys}"
    )


def test_launch_screen_builds_key_mapping_for_plan_view() -> None:
    """LaunchScreen should map keys only for available ACTION commands in plan view."""
    row = make_plan_row(
        123,
        "Test Plan",
        plan_url="https://github.com/test/repo/issues/123",
        pr_number=456,
        pr_url="https://github.com/test/repo/pull/456",
        pr_state="OPEN",
        run_url="https://github.com/test/repo/actions/runs/789",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    screen = LaunchScreen(ctx=ctx)

    # Key mapping is built in __init__, no need to call compose()
    assert "c" in screen._key_to_command_id  # close_plan
    assert "d" in screen._key_to_command_id  # dispatch_to_queue
    assert "l" in screen._key_to_command_id  # land_pr
    assert "r" in screen._key_to_command_id  # rebase_remote
    assert "a" in screen._key_to_command_id  # address_remote
    assert "w" in screen._key_to_command_id  # rewrite_remote

    # Should NOT have objective keys
    assert screen._key_to_command_id.get("k") is None


def test_launch_screen_builds_key_mapping_for_objectives_view() -> None:
    """LaunchScreen should map keys only for available ACTION commands in objectives view."""
    row = make_plan_row(
        123,
        "Test Objective",
        plan_url="https://github.com/test/repo/issues/123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES)
    screen = LaunchScreen(ctx=ctx)

    # Should have objective action keys
    assert "c" in screen._key_to_command_id  # close_objective
    assert "s" in screen._key_to_command_id  # one_shot_plan
    assert "k" in screen._key_to_command_id  # check_objective

    # Should NOT have plan-specific keys
    assert screen._key_to_command_id.get("f") is None
    assert screen._key_to_command_id.get("a") is None


def test_launch_screen_excludes_unavailable_commands() -> None:
    """LaunchScreen should not show commands whose predicates return False."""
    # Row with no PR: rebase_remote and address_remote should be excluded
    row = make_plan_row(
        123,
        "Test Plan",
        plan_url="https://github.com/test/repo/issues/123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    screen = LaunchScreen(ctx=ctx)

    # close_plan and dispatch_to_queue should be present (always available / needs plan_url)
    assert "c" in screen._key_to_command_id
    assert "d" in screen._key_to_command_id

    # rebase_remote and address_remote need pr_number, should be absent
    assert "f" not in screen._key_to_command_id
    assert "a" not in screen._key_to_command_id

    # land_pr needs pr_number + OPEN state + run_url, should be absent
    assert "l" not in screen._key_to_command_id


def test_launch_screen_maps_command_ids_correctly() -> None:
    """Key mappings should resolve to the correct command IDs."""
    row = make_plan_row(
        123,
        "Test Plan",
        plan_url="https://github.com/test/repo/issues/123",
        pr_number=456,
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS)
    screen = LaunchScreen(ctx=ctx)

    assert screen._key_to_command_id["c"] == "close_plan"
    assert screen._key_to_command_id["d"] == "dispatch_to_queue"
    assert screen._key_to_command_id["r"] == "rebase_remote"
    assert screen._key_to_command_id["a"] == "address_remote"
    assert screen._key_to_command_id["w"] == "rewrite_remote"
