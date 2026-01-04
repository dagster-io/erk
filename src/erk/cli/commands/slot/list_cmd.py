"""Slot list command - display unified worktree pool status."""

from pathlib import Path
from typing import Literal

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.commands.slot.common import (
    DEFAULT_POOL_SIZE,
    generate_slot_name,
    get_placeholder_branch_name,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk.core.worktree_pool import PoolState, load_pool_state

SlotStatus = Literal["active", "ready", "empty"]


def _determine_slot_status(
    slot_name: str,
    worktree_path: Path,
    current_branch: str | None,
    assigned_slots: set[str],
    initialized_slots: set[str],
) -> SlotStatus:
    """Determine the status of a worktree slot.

    Args:
        slot_name: The slot identifier (e.g., "erk-managed-wt-01")
        worktree_path: Expected filesystem path for the worktree
        current_branch: Current branch checked out, or None if not exists
        assigned_slots: Set of slot names that have assignments in pool.json
        initialized_slots: Set of slot names that are initialized

    Returns:
        Status: "active" (has assignment), "ready" (initialized, unassigned), "empty"
    """
    # If slot is in pool.json assignments, it's active
    if slot_name in assigned_slots:
        return "active"

    # If slot is initialized (has worktree created), it's ready
    if slot_name in initialized_slots:
        return "ready"

    # Check if worktree exists on filesystem but not tracked
    placeholder_branch = get_placeholder_branch_name(slot_name)
    if current_branch is not None:
        # Worktree exists but not in initialized list
        if placeholder_branch is not None and current_branch == placeholder_branch:
            return "ready"
        # Worktree exists with a non-placeholder branch but not in pool.json
        return "ready"

    # Slot doesn't exist
    return "empty"


def _get_fs_sync_state(
    slot_name: str,
    assigned_branch: str | None,
    actual_branch: str | None,
) -> str:
    """Determine filesystem sync state.

    Args:
        slot_name: Slot name
        assigned_branch: Branch assigned in pool.json (if any)
        actual_branch: Actual branch on filesystem (if any)

    Returns:
        Sync state: "synced", "stale", or "-"
    """
    if actual_branch is None:
        # No worktree on filesystem
        if assigned_branch is not None:
            return "stale"  # pool.json says assigned but no worktree
        return "-"  # Neither assigned nor exists

    if assigned_branch is None:
        # Worktree exists but not assigned
        return "synced"  # Ready state is valid

    # Both exist - check if they match
    if actual_branch == assigned_branch:
        return "synced"
    return "stale"


@alias("ls")
@click.command("list")
@click.pass_obj
def slot_list(ctx: ErkContext) -> None:
    """List all pool slots with unified status view.

    Shows a table combining pool.json state and filesystem state:
    - Worktree: The pool worktree name
    - Status: active (has assignment), ready (initialized), or empty
    - Branch: Assigned branch or "(available)"
    - Assigned: When the assignment was made (relative time)
    - FS State: synced (matches pool.json), stale (mismatch), or -
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state (or use defaults if no state exists)
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=DEFAULT_POOL_SIZE,
            slots=(),
            assignments=(),
        )

    # Build lookup sets
    assigned_slots = {a.slot_name for a in state.assignments}
    initialized_slots = {s.name for s in state.slots}

    # Build lookup of slot_name -> (branch_name, relative_time)
    assignments_by_slot: dict[str, tuple[str, str]] = {}
    for assignment in state.assignments:
        relative_time = format_relative_time(assignment.assigned_at)
        assignments_by_slot[assignment.slot_name] = (assignment.branch_name, relative_time)

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Worktree", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Branch", style="yellow", no_wrap=True)
    table.add_column("Assigned", no_wrap=True)
    table.add_column("FS State", no_wrap=True)

    # Track counts for summary
    active_count = 0
    ready_count = 0

    # Add rows for all slots
    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        worktree_path = repo.worktrees_dir / slot_name

        # Check if worktree exists and get current branch
        worktree_exists = ctx.git.path_exists(worktree_path)

        actual_branch: str | None = None
        if worktree_exists:
            actual_branch = ctx.git.get_current_branch(worktree_path)

        # Determine status
        status = _determine_slot_status(
            slot_name, worktree_path, actual_branch, assigned_slots, initialized_slots
        )

        # Get assigned branch info
        assigned_branch: str | None = None
        assigned_time = "-"
        if slot_name in assignments_by_slot:
            assigned_branch, assigned_time = assignments_by_slot[slot_name]

        # Determine FS sync state
        fs_state = _get_fs_sync_state(slot_name, assigned_branch, actual_branch)

        # Format branch display
        if status == "active":
            branch_display = assigned_branch if assigned_branch else "-"
        elif status == "ready":
            branch_display = "[dim](available)[/dim]"
            assigned_time = "-"
        else:
            branch_display = "[dim](available)[/dim]"
            assigned_time = "-"

        # Format status with color
        status_map = {
            "active": "[green]active[/green]",
            "ready": "[blue]ready[/blue]",
            "empty": "[dim]-[/dim]",
        }
        status_display = status_map[status]

        # Format FS state with color
        fs_state_map = {
            "synced": "[green]synced[/green]",
            "stale": "[red]stale[/red]",
            "-": "[dim]-[/dim]",
        }
        fs_state_display = fs_state_map.get(fs_state, fs_state)

        table.add_row(slot_name, status_display, branch_display, assigned_time, fs_state_display)

        # Track counts
        if status == "active":
            active_count += 1
        elif status == "ready":
            ready_count += 1

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)

    # Print summary
    initialized_count = len(state.slots)
    console.print(
        f"\nPool: {state.pool_size} slots | "
        f"{initialized_count} initialized | "
        f"{active_count} active | "
        f"{ready_count} ready"
    )
