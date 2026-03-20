"""Pure naming utilities for erk slot names.

All functions are pure (no I/O) and follow LBYL patterns.
Only dependency: the standard library ``re`` module.
"""

import re

# Default pool configuration
DEFAULT_POOL_SIZE = 4
SLOT_NAME_PREFIX = "erk-slot"


def extract_slot_number(slot_name: str) -> str | None:
    """Extract slot number from slot name.

    Args:
        slot_name: Slot name like "erk-slot-03"

    Returns:
        Two-digit slot number (e.g., "03") or None if not in expected format
    """
    if not slot_name.startswith(SLOT_NAME_PREFIX + "-"):
        return None
    suffix = slot_name[len(SLOT_NAME_PREFIX) + 1 :]
    if len(suffix) != 2 or not suffix.isdigit():
        return None
    return suffix


def get_placeholder_branch_name(slot_name: str) -> str | None:
    """Get placeholder branch name for a slot.

    Args:
        slot_name: Slot name like "erk-slot-03"

    Returns:
        Placeholder branch name like "__erk-slot-03-br-stub__",
        or None if slot_name is not in expected format
    """
    slot_number = extract_slot_number(slot_name)
    if slot_number is None:
        return None
    return f"__erk-slot-{slot_number}-br-stub__"


def is_placeholder_branch(branch_name: str) -> bool:
    """Check if a branch name is an erk slot placeholder branch.

    Placeholder branches have the format: __erk-slot-XX-br-stub__

    Args:
        branch_name: Branch name to check

    Returns:
        True if branch_name matches the placeholder pattern
    """
    return bool(re.match(r"^__erk-slot-\d+-br-stub__$", branch_name))


def generate_slot_name(slot_number: int) -> str:
    """Generate a slot name from a slot number.

    Args:
        slot_number: 1-based slot number

    Returns:
        Formatted slot name like "erk-slot-01"
    """
    return f"{SLOT_NAME_PREFIX}-{slot_number:02d}"
