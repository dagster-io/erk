"""Shared utilities for pooled branch commands."""

from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment
from erk_shared.output.output import user_confirm, user_output

# Default pool configuration
DEFAULT_POOL_SIZE = 4
SLOT_NAME_PREFIX = "erk-managed-wt"


def get_pool_size(ctx: ErkContext) -> int:
    """Get effective pool size from config or default.

    Args:
        ctx: Current erk context with local_config

    Returns:
        Configured pool size or DEFAULT_POOL_SIZE if not set
    """
    if ctx.local_config is not None and ctx.local_config.pool_size is not None:
        return ctx.local_config.pool_size
    return DEFAULT_POOL_SIZE


def generate_slot_name(slot_number: int) -> str:
    """Generate a slot name from a slot number.

    Args:
        slot_number: 1-based slot number

    Returns:
        Formatted slot name like "erk-managed-wt-01"
    """
    return f"{SLOT_NAME_PREFIX}-{slot_number:02d}"


def find_next_available_slot(state: PoolState) -> int | None:
    """Find the next available slot number.

    Args:
        state: Current pool state

    Returns:
        1-based slot number if available, None if pool is full
    """
    assigned_slots = {a.slot_name for a in state.assignments}

    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        if slot_name not in assigned_slots:
            return slot_num

    return None


def find_branch_assignment(state: PoolState, branch_name: str) -> SlotAssignment | None:
    """Find if a branch is already assigned to a slot.

    Args:
        state: Current pool state
        branch_name: Branch to search for

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.branch_name == branch_name:
            return assignment
    return None


def find_oldest_assignment(state: PoolState) -> SlotAssignment | None:
    """Find the oldest assignment by assigned_at timestamp.

    Args:
        state: Current pool state

    Returns:
        The oldest SlotAssignment, or None if no assignments
    """
    if not state.assignments:
        return None

    oldest: SlotAssignment | None = None
    for assignment in state.assignments:
        if oldest is None or assignment.assigned_at < oldest.assigned_at:
            oldest = assignment
    return oldest


def display_pool_assignments(state: PoolState) -> None:
    """Display current pool assignments to user.

    Args:
        state: Current pool state
    """
    user_output("\nCurrent pool assignments:")
    for assignment in sorted(state.assignments, key=lambda a: a.assigned_at):
        slot = assignment.slot_name
        branch = assignment.branch_name
        assigned = assignment.assigned_at
        user_output(f"  {slot}: {branch} (assigned {assigned})")
    user_output("")


def handle_pool_full_interactive(
    state: PoolState,
    force: bool,
    is_tty: bool,
) -> SlotAssignment | None:
    """Handle pool-full condition: prompt to unassign oldest or error.

    When the pool is full:
    - If --force: auto-unassign the oldest assignment
    - If interactive (TTY): show assignments and prompt user
    - If non-interactive (no TTY): error with instructions

    Args:
        state: Current pool state
        force: If True, auto-unassign oldest without prompting
        is_tty: Whether running in an interactive terminal

    Returns:
        SlotAssignment to unassign, or None if user declined/error
    """
    oldest = find_oldest_assignment(state)
    if oldest is None:
        return None

    if force:
        user_output(f"Pool is full. --force specified, unassigning oldest: {oldest.branch_name}")
        return oldest

    if not is_tty:
        slots = len(state.assignments)
        user_output(
            f"Error: Pool is full ({slots} slots). "
            "Use --force to auto-unassign the oldest branch, "
            "or run `erk pooled list` to see assignments."
        )
        return None

    # Interactive mode: show assignments and prompt
    display_pool_assignments(state)
    user_output(f"Pool is full ({len(state.assignments)} slots).")
    user_output(f"Oldest assignment: {oldest.branch_name} ({oldest.slot_name})")

    if user_confirm(f"Unassign '{oldest.branch_name}' to make room?", default=False):
        return oldest

    user_output("Aborted.")
    return None
