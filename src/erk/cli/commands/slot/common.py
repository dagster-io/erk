"""Shared utilities for slot commands."""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import click

from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext, ensure_erk_metadata_dir
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.console.abc import Console
from erk_shared.git.abc import Git
from erk_shared.output.output import user_output


@dataclass(frozen=True)
class SlotAllocationResult:
    """Result of allocating a slot for a branch."""

    slot_name: str
    worktree_path: Path
    already_assigned: bool  # True if branch was already in a slot


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
        Formatted slot name like "erk-slot-01"
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


def find_inactive_slot(
    state: PoolState,
    git: Git,
    repo_root: Path,
) -> tuple[str, Path] | None:
    """Find an available managed slot for reuse.

    Searches for worktrees that exist but are not assigned.
    Uses git as source of truth for which worktrees exist.
    Prefers slots in order (lowest slot number first).

    Args:
        state: Current pool state
        git: Git gateway for worktree operations
        repo_root: Repository root path

    Returns:
        Tuple of (slot_name, worktree_path) for an available slot,
        or None if no inactive slot found
    """
    assigned_slots = {a.slot_name for a in state.assignments}

    # Get all worktrees from git (source of truth)
    worktrees = git.list_worktrees(repo_root)

    # Build lookup of slot_name -> worktree_path for managed slots
    managed_worktrees: dict[str, Path] = {}
    for wt in worktrees:
        slot_name = wt.path.name
        if extract_slot_number(slot_name) is not None:
            managed_worktrees[slot_name] = wt.path

    # Find first unassigned slot (by slot number order)
    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        if slot_name in managed_worktrees and slot_name not in assigned_slots:
            return (slot_name, managed_worktrees[slot_name])

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
    console: Console,
    state: PoolState,
    *,
    force: bool,
) -> SlotAssignment | None:
    """Handle pool-full condition: prompt to unassign oldest or error.

    When the pool is full:
    - If --force: auto-unassign the oldest assignment
    - If interactive (TTY): show assignments and prompt user
    - If non-interactive (no TTY): error with instructions

    Args:
        console: Console for user prompts
        state: Current pool state
        force: If True, auto-unassign oldest without prompting

    Returns:
        SlotAssignment to unassign, or None if user declined/error
    """
    oldest = find_oldest_assignment(state)
    if oldest is None:
        return None

    if force:
        user_output(f"Pool is full. --force specified, unassigning oldest: {oldest.branch_name}")
        return oldest

    if not console.is_stdin_interactive():
        user_output(
            f"Error: Pool is full ({state.pool_size} slots). "
            "Use --force to auto-unassign the oldest branch, "
            "or run `erk slot list` to see assignments."
        )
        return None

    # Interactive mode: show assignments and prompt
    display_pool_assignments(state)
    user_output(f"Pool is full ({state.pool_size} slots).")
    user_output(f"Oldest assignment: {oldest.branch_name} ({oldest.slot_name})")

    if console.confirm(f"Unassign '{oldest.branch_name}' to make room?", default=False):
        return oldest

    user_output("Aborted.")
    return None


def cleanup_worktree_artifacts(worktree_path: Path) -> None:
    """Remove stale artifacts from a worktree before reuse.

    Cleans up .impl/ and .erk/scratch/ folders which persist across
    branch switches since they are in .gitignore.

    Args:
        worktree_path: Path to the worktree to clean up
    """
    impl_folder = worktree_path / ".impl"
    scratch_folder = worktree_path / ".erk" / "scratch"

    if impl_folder.exists():
        shutil.rmtree(impl_folder)

    if scratch_folder.exists():
        shutil.rmtree(scratch_folder)


def allocate_slot_for_branch(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    *,
    force: bool,
    reuse_inactive_slots: bool,
    cleanup_artifacts: bool,
) -> SlotAllocationResult:
    """Allocate a pool slot for a branch and setup the worktree.

    This is the unified slot allocation algorithm used by all commands
    that need to assign branches to pool slots.

    The branch MUST already exist before calling this function.

    Args:
        ctx: Erk context (uses ctx.time.now() for testable timestamps)
        repo: Repository context with pool_json_path and worktrees_dir
        branch_name: Name of existing branch to assign
        force: Auto-unassign oldest if pool is full (no interactive prompt)
        reuse_inactive_slots: Try to reuse unassigned worktrees first
        cleanup_artifacts: Remove .impl/ and .erk/scratch/ on worktree reuse

    Returns:
        SlotAllocationResult with slot info

    Raises:
        SystemExit(1): If pool is full and user declined to unassign
    """
    ensure_erk_metadata_dir(repo)

    # Get pool size from config or default
    pool_size = get_pool_size(ctx)

    # Load or create pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        state = PoolState(
            version="1.0",
            pool_size=pool_size,
            slots=(),
            assignments=(),
        )

    # Check if branch is already assigned
    existing = find_branch_assignment(state, branch_name)
    if existing is not None:
        # Branch is already assigned to a slot - just return that path
        return SlotAllocationResult(
            slot_name=existing.slot_name,
            worktree_path=existing.worktree_path,
            already_assigned=True,
        )

    # First, prefer reusing existing worktrees (fast path)
    inactive_slot = None
    if reuse_inactive_slots:
        inactive_slot = find_inactive_slot(state, ctx.git, repo.root)

    if inactive_slot is not None:
        slot_name, worktree_path = inactive_slot
        if cleanup_artifacts:
            cleanup_worktree_artifacts(worktree_path)
        ctx.git.checkout_branch(worktree_path, branch_name)
    else:
        # Fall back to on-demand slot creation
        slot_num = find_next_available_slot(state, repo.worktrees_dir)
        if slot_num is None:
            # Pool is full - handle interactively or with --force
            to_unassign = handle_pool_full_interactive(ctx.console, state, force=force)
            if to_unassign is None:
                raise SystemExit(1) from None

            # Remove the assignment from state
            new_assignments = tuple(
                a for a in state.assignments if a.slot_name != to_unassign.slot_name
            )
            state = PoolState(
                version=state.version,
                pool_size=state.pool_size,
                slots=state.slots,
                assignments=new_assignments,
            )
            save_pool_state(repo.pool_json_path, state)
            user_output(
                click.style("✓ ", fg="green")
                + f"Unassigned {click.style(to_unassign.branch_name, fg='yellow')} "
                + f"from {click.style(to_unassign.slot_name, fg='cyan')}"
            )

            # Reuse the unassigned slot
            slot_name = to_unassign.slot_name
            worktree_path = to_unassign.worktree_path

            # Check if worktree directory actually exists
            if worktree_path.exists():
                # Worktree exists - clean up and checkout
                if cleanup_artifacts:
                    cleanup_worktree_artifacts(worktree_path)
                ctx.git.checkout_branch(worktree_path, branch_name)
            else:
                # Worktree doesn't exist (orphaned assignment) - create it
                worktree_path.mkdir(parents=True, exist_ok=True)
                ctx.git.add_worktree(
                    repo.root,
                    worktree_path,
                    branch=branch_name,
                    ref=None,
                    create_branch=False,
                )
        else:
            # Create new slot - no worktree exists yet
            slot_name = generate_slot_name(slot_num)
            worktree_path = repo.worktrees_dir / slot_name
            worktree_path.mkdir(parents=True, exist_ok=True)
            ctx.git.add_worktree(
                repo.root,
                worktree_path,
                branch=branch_name,
                ref=None,
                create_branch=False,
            )

    # Create new assignment
    now = ctx.time.now().isoformat()
    new_assignment = SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=now,
        worktree_path=worktree_path,
    )

    # Update state with new assignment
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=state.slots,
        assignments=(*state.assignments, new_assignment),
    )

    # Save state
    save_pool_state(repo.pool_json_path, new_state)

    return SlotAllocationResult(
        slot_name=slot_name,
        worktree_path=worktree_path,
        already_assigned=False,
    )
