"""Tests for the LaunchScreen modal."""

from erk.tui.commands.registry import get_all_commands
from erk.tui.commands.types import CommandCategory, CommandContext
from erk.tui.screens.launch_screen import LAUNCH_KEYS, LaunchScreen
from erk.tui.views.types import ViewMode
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_launch_keys_only_maps_action_commands() -> None:
    """All command IDs in LAUNCH_KEYS should be ACTION category commands."""
    all_commands = get_all_commands()
    action_ids = {cmd.id for cmd in all_commands if cmd.category == CommandCategory.ACTION}
    for command_id in LAUNCH_KEYS:
        assert command_id in action_ids, (
            f"LAUNCH_KEYS maps {command_id} but it's not an ACTION command"
        )


def test_launch_keys_no_duplicate_keys_within_plan_view() -> None:
    """Plan action keys should not have duplicate key bindings."""
    plan_action_ids = [
        "close_plan",
        "submit_to_queue",
        "land_pr",
        "fix_conflicts_remote",
        "address_remote",
    ]
    keys = [LAUNCH_KEYS[cid] for cid in plan_action_ids if cid in LAUNCH_KEYS]
    assert len(keys) == len(set(keys)), f"Duplicate keys in plan actions: {keys}"


def test_launch_keys_no_duplicate_keys_within_objective_view() -> None:
    """Objective action keys should not have duplicate key bindings."""
    obj_action_ids = ["close_objective", "one_shot_plan", "check_objective"]
    keys = [LAUNCH_KEYS[cid] for cid in obj_action_ids if cid in LAUNCH_KEYS]
    assert len(keys) == len(set(keys)), f"Duplicate keys in objective actions: {keys}"


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
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    screen = LaunchScreen(ctx=ctx)

    # Key mapping is built in __init__, no need to call compose()
    assert "c" in screen._key_to_command_id  # close_plan
    assert "s" in screen._key_to_command_id  # submit_to_queue
    assert "l" in screen._key_to_command_id  # land_pr
    assert "f" in screen._key_to_command_id  # fix_conflicts_remote
    assert "a" in screen._key_to_command_id  # address_remote

    # Should NOT have objective keys
    assert screen._key_to_command_id.get("k") is None


def test_launch_screen_builds_key_mapping_for_objectives_view() -> None:
    """LaunchScreen should map keys only for available ACTION commands in objectives view."""
    row = make_plan_row(
        123,
        "Test Objective",
        plan_url="https://github.com/test/repo/issues/123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.OBJECTIVES, plan_backend="github")
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
    # Row with no PR: fix_conflicts_remote and address_remote should be excluded
    row = make_plan_row(
        123,
        "Test Plan",
        plan_url="https://github.com/test/repo/issues/123",
    )
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    screen = LaunchScreen(ctx=ctx)

    # close_plan and submit_to_queue should be present (always available / needs plan_url)
    assert "c" in screen._key_to_command_id
    assert "s" in screen._key_to_command_id

    # fix_conflicts_remote and address_remote need pr_number, should be absent
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
    ctx = CommandContext(row=row, view_mode=ViewMode.PLANS, plan_backend="github")
    screen = LaunchScreen(ctx=ctx)

    assert screen._key_to_command_id["c"] == "close_plan"
    assert screen._key_to_command_id["s"] == "submit_to_queue"
    assert screen._key_to_command_id["f"] == "fix_conflicts_remote"
    assert screen._key_to_command_id["a"] == "address_remote"
