"""Shared utilities for slot commands."""

from pathlib import Path

from erk.core.context import ErkContext
from erk.core.worktree_pool import PoolState, SlotAssignment, SlotInfo
from erk_shared.git.abc import Git
from erk_shared.output.output import user_confirm, user_output

# Default pool configuration
DEFAULT_POOL_SIZE = 4
SLOT_NAME_PREFIX = "erk-managed-wt"


def extract_slot_number(slot_name: str) -> str | None:
    """Extract slot number from slot name.

    Args:
        slot_name: Slot name like "erk-managed-wt-03"

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
        slot_name: Slot name like "erk-managed-wt-03"

    Returns:
        Placeholder branch name like "__erk-slot-03-placeholder__",
        or None if slot_name is not in expected format
    """
    slot_number = extract_slot_number(slot_name)
    if slot_number is None:
        return None
    return f"__erk-slot-{slot_number}-placeholder__"


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


def find_next_available_slot(state: PoolState, worktrees_dir: Path | None) -> int | None:
    """Find the next available slot number for on-demand worktree creation.

    This function finds a slot number that is:
    1. Not currently assigned to a branch (not in state.assignments)
    2. Not already initialized as a worktree (not in state.slots)
    3. Does not have an orphaned directory on disk (if worktrees_dir provided)

    This ensures on-demand creation only targets slots where no worktree
    exists on disk.

    Args:
        state: Current pool state
        worktrees_dir: Directory containing worktrees, or None to skip disk check

    Returns:
        1-based slot number if available, None if pool is full
    """
    assigned_slots = {a.slot_name for a in state.assignments}
    initialized_slots = {s.name for s in state.slots}

    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        if slot_name not in assigned_slots and slot_name not in initialized_slots:
            # Check if directory exists on disk (orphaned worktree)
            if worktrees_dir is not None:
                slot_path = worktrees_dir / slot_name
                if slot_path.exists():
                    continue  # Skip - directory exists but not tracked
            return slot_num

    return None


def find_inactive_slot(state: PoolState) -> SlotInfo | None:
    """Find an initialized slot without an active assignment.

    Prefers returning slots in order (lowest slot number first).

    Args:
        state: Current pool state

    Returns:
        SlotInfo for an inactive initialized slot, or None if none available
    """
    assigned_slots = {a.slot_name for a in state.assignments}

    for slot in state.slots:
        if slot.name not in assigned_slots:
            return slot

    return None


def is_slot_initialized(state: PoolState, slot_name: str) -> bool:
    """Check if a slot has been initialized.

    Args:
        state: Current pool state
        slot_name: Name of the slot to check

    Returns:
        True if slot is in the initialized slots list
    """
    return any(slot.name == slot_name for slot in state.slots)


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


def find_assignment_by_worktree(state: PoolState, git: Git, cwd: Path) -> SlotAssignment | None:
    """Find if cwd is within a managed slot using git.

    Uses git to determine the worktree root of cwd, then matches exactly
    against known slot assignments. This is more reliable than path
    comparisons which can fail with symlinks, relative paths, etc.

    Args:
        state: Current pool state
        git: Git gateway for repository operations
        cwd: Current working directory

    Returns:
        SlotAssignment if cwd is within a managed slot, None otherwise
    """
    worktree_root = git.get_repository_root(cwd)
    for assignment in state.assignments:
        if assignment.worktree_path == worktree_root:
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
            "or run `erk slot list` to see assignments."
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
