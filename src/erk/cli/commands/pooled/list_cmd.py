"""Pooled list command - display worktree pool status."""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.alias import alias
from erk.cli.commands.pooled.common import DEFAULT_POOL_SIZE, generate_slot_name
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk.core.worktree_pool import PoolState, load_pool_state


@alias("ls")
@click.command("list")
@click.pass_obj
def pooled_list(ctx: ErkContext) -> None:
    """List all pool slots and their assignments.

    Shows a table with:
    - Slot: The pool slot name
    - Status: active (assigned), ready (initialized), uninitialized
    - Branch: Assigned branch or "(available)"
    - Assigned: When the assignment was made
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state (or use defaults if no state exists)
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=DEFAULT_POOL_SIZE,
            assignments=(),
            slots=(),
        )

    # Build lookup of slot_name -> assignment
    assignments_by_slot: dict[str, tuple[str, str]] = {}
    for assignment in state.assignments:
        relative_time = format_relative_time(assignment.assigned_at)
        assignments_by_slot[assignment.slot_name] = (assignment.branch_name, relative_time)

    # Build set of initialized slot names
    initialized_slots: set[str] = {slot.name for slot in state.slots}

    # Create Rich table
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Slot", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Branch", style="yellow", no_wrap=True)
    table.add_column("Assigned", no_wrap=True)

    # Add rows for all slots
    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)

        if slot_name in assignments_by_slot:
            # Active: has assignment
            branch_name, assigned_time = assignments_by_slot[slot_name]
            status = "[green]active[/green]"
            table.add_row(slot_name, status, branch_name, assigned_time)
        elif slot_name in initialized_slots:
            # Ready: initialized but no assignment
            status = "[cyan]ready[/cyan]"
            table.add_row(slot_name, status, "[dim](available)[/dim]", "-")
        else:
            # Uninitialized: not in slots array
            status = "[dim]uninitialized[/dim]"
            table.add_row(slot_name, status, "[dim]-[/dim]", "-")

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, force_terminal=True)
    console.print(table)
