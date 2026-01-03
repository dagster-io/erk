"""Shared utilities for pooled branch commands."""

from erk.core.worktree_pool import PoolState, SlotAssignment

# Default pool configuration
DEFAULT_POOL_SIZE = 4
SLOT_NAME_PREFIX = "erk-managed-wt"


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
