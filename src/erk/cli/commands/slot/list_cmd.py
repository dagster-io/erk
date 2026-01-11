"""Slot list command - display unified worktree pool status."""

from typing import Literal

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.commands.slot.common import (
    DEFAULT_POOL_SIZE,
    generate_slot_name,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk.core.worktree_pool import PoolState, load_pool_state

SlotStatus = Literal["available", "assigned", "error"]
SlotReason = Literal["worktree-missing", "branch-mismatch", "-"]


def _determine_slot_status(
    slot_name: str,
    assigned_slots: set[str],
    reason: SlotReason,
) -> SlotStatus:
    """Determine the status of a worktree slot.

    Args:
        slot_name: The slot identifier (e.g., "erk-slot-01")
        assigned_slots: Set of slot names that have assignments in pool.json
        reason: The reason code from _get_slot_reason (indicates any problems)

    Returns:
        Status: "assigned" (healthy assignment), "error" (assignment with problem),
                "available" (can be used)
    """
    # If slot has an assignment in pool.json
    if slot_name in assigned_slots:
        # Check if there's a problem with the assignment
        if reason != "-":
            return "error"
        return "assigned"

    # No assignment - slot is available
    return "available"


def _get_slot_reason(
    assigned_branch: str | None,
    actual_branch: str | None,
    *,
    same_stack: bool,
) -> SlotReason:
    """Determine the reason for slot state.

    Returns a kebab-case reason explaining any issues with the slot:
    - "worktree-missing": pool.json has assignment but worktree doesn't exist
    - "branch-mismatch": worktree exists but has different branch than assignment
    - "-": healthy state (no problem)

    Args:
        assigned_branch: Branch assigned in pool.json (if any)
        actual_branch: Actual branch on filesystem (if any)
        same_stack: Whether actual_branch is in the same stack as assigned_branch

    Returns:
        Reason literal explaining any issues
    """
    if actual_branch is None:
        # No worktree on filesystem
        if assigned_branch is not None:
            return "worktree-missing"  # pool.json says assigned but no worktree
        return "-"  # Neither assigned nor exists - healthy available state

    if assigned_branch is None:
        # Worktree exists but not assigned - healthy available state
        return "-"

    # Both exist - check if they match
    if actual_branch == assigned_branch:
        return "-"  # Healthy - branches match
    if same_stack:
        return "-"  # Stacked branch is healthy
    return "branch-mismatch"


@alias("ls")
@click.command("list")
@click.pass_obj
def slot_list(ctx: ErkContext) -> None:
    """List all pool slots with unified status view.

    Shows a table combining pool.json state and filesystem state:
    - Worktree: The pool worktree name
    - Branch: Assigned branch or - (available)
    - Assigned: When the assignment was made (relative time)
    - Status: available, assigned (healthy), or error (has problem)
    - Reason: worktree-missing, branch-mismatch, or - (healthy)
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

    # Build lookup set
    assigned_slots = {a.slot_name for a in state.assignments}

    # Build lookup of slot_name -> (branch_name, relative_time)
    assignments_by_slot: dict[str, tuple[str, str]] = {}
    for assignment in state.assignments:
        relative_time = format_relative_time(assignment.assigned_at)
        assignments_by_slot[assignment.slot_name] = (assignment.branch_name, relative_time)

    # Build lookup of slot_name -> last_objective_issue
    objectives_by_slot: dict[str, int] = {}
    for slot in state.slots:
        if slot.last_objective_issue is not None:
            objectives_by_slot[slot.name] = slot.last_objective_issue

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Worktree", style="cyan", no_wrap=True)
    table.add_column("Exists", no_wrap=True)
    table.add_column("Branch", style="yellow", no_wrap=True)
    table.add_column("Objective", no_wrap=True)
    table.add_column("Assigned", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Reason", no_wrap=True)
    table.add_column("Changes", no_wrap=True)

    # Track counts for summary
    assigned_count = 0
    error_count = 0

    # Add rows for all slots
    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        worktree_path = repo.worktrees_dir / slot_name

        # Check if worktree exists and get current branch
        worktree_exists = ctx.git.path_exists(worktree_path)

        actual_branch: str | None = None
        if worktree_exists:
            actual_branch = ctx.git.get_current_branch(worktree_path)

        # Get assigned branch info
        assigned_branch: str | None = None
        assigned_time = "-"
        if slot_name in assignments_by_slot:
            assigned_branch, assigned_time = assignments_by_slot[slot_name]

        # Check if branches are in the same stack (stacked branches are healthy)
        same_stack = False
        if assigned_branch is not None and actual_branch is not None:
            if assigned_branch != actual_branch:
                stack = ctx.branch_manager.get_branch_stack(repo.root, assigned_branch)
                if stack is not None and actual_branch in stack:
                    same_stack = True

        # Determine reason for any issues (needed before status)
        reason = _get_slot_reason(assigned_branch, actual_branch, same_stack=same_stack)

        # Determine status (depends on reason)
        status = _determine_slot_status(slot_name, assigned_slots, reason)

        # Format branch display
        if status == "available":
            branch_display = "[dim]-[/dim]"
            assigned_time = "-"
        else:
            # Both "assigned" and "error" show the assigned branch
            branch_display = assigned_branch if assigned_branch else "-"

        # Format status with color
        status_map: dict[SlotStatus, str] = {
            "available": "[dim]available[/dim]",
            "assigned": "[green]assigned[/green]",
            "error": "[red]error[/red]",
        }
        status_display = status_map[status]

        # Format reason with color (only shown for error states)
        reason_map: dict[SlotReason, str] = {
            "worktree-missing": "[red]worktree-missing[/red]",
            "branch-mismatch": "[red]branch-mismatch[/red]",
            "-": "[dim]-[/dim]",
        }
        reason_display = reason_map[reason]

        # Format changes display
        changes_display: str
        if worktree_exists and ctx.git.has_uncommitted_changes(worktree_path):
            changes_display = "[yellow]dirty[/yellow]"
        else:
            changes_display = "[dim]-[/dim]"

        # Format objective display
        objective_display: str
        if slot_name in objectives_by_slot:
            objective_display = f"#{objectives_by_slot[slot_name]}"
        else:
            objective_display = "[dim]-[/dim]"

        # Format exists display
        exists_display = "[green]yes[/green]" if worktree_exists else "[dim]-[/dim]"

        table.add_row(
            slot_name,
            exists_display,
            branch_display,
            objective_display,
            assigned_time,
            status_display,
            reason_display,
            changes_display,
        )

        # Track counts
        if status == "assigned":
            assigned_count += 1
        elif status == "error":
            error_count += 1

    # Output table to stderr (consistent with user_output convention)
    # Use width=200 to ensure proper display without truncation
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)

    # Print summary
    available_count = state.pool_size - assigned_count - error_count
    console.print(
        f"\nPool: {state.pool_size} slots | "
        f"{available_count} available | "
        f"{assigned_count} assigned | "
        f"{error_count} error"
    )
