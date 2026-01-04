"""Shared utilities for pooled branch commands."""

import re

from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment, SlotInfo
from erk_shared.output.output import user_confirm, user_output

# Default pool configuration
DEFAULT_POOL_SIZE = 4
SLOT_NAME_PREFIX = "erk-managed-wt"
PLACEHOLDER_BRANCH_PREFIX = "__erk-slot"
PLACEHOLDER_BRANCH_SUFFIX = "placeholder__"


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


def generate_placeholder_branch_name(slot_number: int) -> str:
    """Generate a placeholder branch name for a slot.

    Args:
        slot_number: 1-based slot number

    Returns:
        Formatted placeholder branch name like "__erk-slot-01-placeholder__"
    """
    return f"{PLACEHOLDER_BRANCH_PREFIX}-{slot_number:02d}-{PLACEHOLDER_BRANCH_SUFFIX}"


def get_slot_number_from_name(slot_name: str) -> int | None:
    """Extract the slot number from a slot name.

    Args:
        slot_name: Slot name like "erk-managed-wt-01"

    Returns:
        1-based slot number if valid, None otherwise
    """
    pattern = re.compile(rf"^{re.escape(SLOT_NAME_PREFIX)}-(\d+)$")
    match = pattern.match(slot_name)
    if match is None:
        return None
    return int(match.group(1))


def is_slot_initialized(state: PoolState, slot_name: str) -> bool:
    """Check if a slot is in the initialized slots list.

    Args:
        state: Current pool state
        slot_name: Slot name to check

    Returns:
        True if the slot is in the slots list, False otherwise
    """
    for slot in state.slots:
        if slot.name == slot_name:
            return True
    return False


def find_inactive_slot(state: PoolState) -> SlotInfo | None:
    """Find an initialized slot that has no current assignment.

    An inactive slot is one that:
    - Exists in state.slots (has been initialized with a placeholder branch)
    - Does NOT have a corresponding entry in state.assignments

    Args:
        state: Current pool state

    Returns:
        SlotInfo for the first inactive slot, or None if all slots are active
    """
    assigned_slot_names = {a.slot_name for a in state.assignments}

    for slot in state.slots:
        if slot.name not in assigned_slot_names:
            return slot

    return None


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
