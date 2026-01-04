"""Slots list command - display worktree slots with actual filesystem state."""

from pathlib import Path
from typing import Literal

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.commands.pooled.common import (
    DEFAULT_POOL_SIZE,
    generate_slot_name,
    get_placeholder_branch_name,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, load_pool_state

SlotStatus = Literal["assigned", "available", "empty"]


def _determine_slot_status(
    slot_name: str,
    worktree_path: Path,
    current_branch: str | None,
    assigned_slots: set[str],
) -> SlotStatus:
    """Determine the status of a worktree slot.

    Args:
        slot_name: The slot identifier (e.g., "erk-managed-wt-01")
        worktree_path: Expected filesystem path for the worktree
        current_branch: Current branch checked out, or None if not exists
        assigned_slots: Set of slot names that have assignments in pool.json

    Returns:
        Status: "assigned" (in pool.json), "available" (exists, unassigned), "empty"
    """
    # If slot is in pool.json assignments, it's assigned
    if slot_name in assigned_slots:
        return "assigned"

    # If worktree exists but not assigned, it's available
    # A placeholder branch indicates the worktree was created but not assigned
    placeholder_branch = get_placeholder_branch_name(slot_name)
    if current_branch is not None:
        # Worktree exists
        if placeholder_branch is not None and current_branch == placeholder_branch:
            return "available"
        # Worktree exists with a non-placeholder branch but not in pool.json
        # This is an inconsistent state - treat as available since it's untracked
        return "available"

    # Worktree doesn't exist
    return "empty"


@alias("ls")
@click.command("list")
@click.pass_obj
def slots_list(ctx: ErkContext) -> None:
    """List worktree slots with their actual state.

    Shows a table with:
    - Slot: The pool slot name
    - Branch: Current git branch (from filesystem, not pool.json)
    - Status: assigned/available/empty
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

    # Build lookup of assigned slot names
    assigned_slots = {a.slot_name for a in state.assignments}

    # Build lookup of slot_name -> branch_name for assigned slots
    assigned_branches: dict[str, str] = {}
    for assignment in state.assignments:
        assigned_branches[assignment.slot_name] = assignment.branch_name

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slot", style="cyan", no_wrap=True)
    table.add_column("Branch", style="yellow", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    # Add rows for all slots
    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        worktree_path = repo.worktrees_dir / slot_name

        # Check if worktree exists and get current branch
        worktree_exists = ctx.git.path_exists(worktree_path)

        current_branch: str | None = None
        if worktree_exists:
            current_branch = ctx.git.get_current_branch(worktree_path)

        # Determine status
        status = _determine_slot_status(slot_name, worktree_path, current_branch, assigned_slots)

        # Format branch
        if status == "assigned":
            # Show assigned branch from pool.json
            branch_display = assigned_branches.get(slot_name, "-")
        elif status == "available":
            # Show actual branch from filesystem
            branch_display = current_branch if current_branch else "-"
        else:
            # Empty slot
            branch_display = "-"

        # Format status with color
        status_map = {
            "assigned": "[green]assigned[/green]",
            "available": "[yellow]available[/yellow]",
            "empty": "[dim]empty[/dim]",
        }
        status_display = status_map[status]

        table.add_row(slot_name, branch_display, status_display)

    # Output table to stderr (consistent with user_output convention)
    # Use width=200 to prevent truncation in terminal environments with narrow defaults
    console = Console(stderr=True, force_terminal=True, width=200)
    console.print(table)
