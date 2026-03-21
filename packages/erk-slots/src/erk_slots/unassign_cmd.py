"""Slot unassign command - remove a branch assignment from a pool slot."""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
    save_pool_state,
)
from erk.core.worktree_utils import get_worktree_branch
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.output.output import user_output
from erk_shared.pr_store.types import PlanState
from erk_shared.slots.naming import get_placeholder_branch_name
from erk_shared.worktree_cleanup import (
    close_plan_for_worktree,
    close_pr_for_branch,
    delete_branch,
    get_plan_info_for_worktree,
    get_pr_info_for_branch,
)


@dataclass(frozen=True)
class UnassignResult:
    """Result of an unassign operation."""

    branch_name: str
    slot_name: str
    trunk_branch: str


def execute_unassign(
    ctx: ErkContext,
    repo: RepoContext,
    state: PoolState,
    assignment: SlotAssignment,
) -> UnassignResult:
    """Execute the unassign operation for a pool slot.

    This function handles:
    - Checking for uncommitted changes
    - Getting or creating placeholder branch
    - Checking out placeholder branch
    - Removing assignment from pool state

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        state: Current pool state
        assignment: The assignment to remove

    Returns:
        UnassignResult with branch name, slot name, and trunk branch

    Raises:
        SystemExit: If worktree has uncommitted changes or placeholder branch cannot be determined
    """
    # Check for uncommitted changes before switching branches
    if ctx.git.status.has_uncommitted_changes(assignment.worktree_path):
        user_output(
            f"Error: Worktree has uncommitted changes at {assignment.worktree_path}.\n"
            "Commit or stash your changes before unassigning."
        )
        raise SystemExit(1) from None

    # Get or create placeholder branch
    placeholder_branch = get_placeholder_branch_name(assignment.slot_name)
    if placeholder_branch is None:
        user_output(
            f"Error: Could not determine placeholder branch for slot {assignment.slot_name}."
        )
        raise SystemExit(1) from None

    trunk_branch = ctx.git.branch.detect_trunk_branch(repo.root)
    local_branches = ctx.git.branch.list_local_branches(repo.root)

    if placeholder_branch not in local_branches:
        create_result = ctx.git.branch.create_branch(
            repo.root, placeholder_branch, trunk_branch, force=False
        )
        if isinstance(create_result, BranchAlreadyExists):
            user_output(f"Error: {create_result.message}")
            raise SystemExit(1) from None
    else:
        # Force-update existing placeholder to trunk so the slot worktree
        # starts fresh after unassignment (e.g., after erk land)
        ctx.git.branch.create_branch(repo.root, placeholder_branch, trunk_branch, force=True)

    # Checkout placeholder branch in the worktree
    ctx.branch_manager.checkout_branch(assignment.worktree_path, placeholder_branch)

    # Remove assignment from state (immutable update)
    new_assignments = tuple(a for a in state.assignments if a.slot_name != assignment.slot_name)
    new_state = PoolState(
        version=state.version,
        pool_size=state.pool_size,
        slots=state.slots,
        assignments=new_assignments,
    )

    # Save updated state (guard for dry-run mode)
    if ctx.dry_run:
        user_output("[DRY RUN] Would save pool state")
    else:
        save_pool_state(repo.pool_json_path, new_state)

    return UnassignResult(
        branch_name=assignment.branch_name,
        slot_name=assignment.slot_name,
        trunk_branch=trunk_branch,
    )


def _find_assignment_by_slot(state: PoolState, slot_name: str) -> SlotAssignment | None:
    """Find an assignment by slot name.

    Args:
        state: Current pool state
        slot_name: A slot name (e.g., "erk-slot-01")

    Returns:
        SlotAssignment if found, None otherwise
    """
    for assignment in state.assignments:
        if assignment.slot_name == slot_name:
            return assignment
    return None


def _find_assignment_by_cwd(state: PoolState, cwd: Path) -> SlotAssignment | None:
    """Find an assignment by checking if cwd is within a pool slot's worktree.

    Args:
        state: Current pool state
        cwd: Current working directory

    Returns:
        SlotAssignment if cwd is within a pool slot, None otherwise
    """
    if not cwd.exists():
        return None
    resolved_cwd = cwd.resolve()
    for assignment in state.assignments:
        if not assignment.worktree_path.exists():
            continue
        wt_path = assignment.worktree_path.resolve()
        if resolved_cwd == wt_path or wt_path in resolved_cwd.parents:
            return assignment
    return None


def _display_planned_operations(
    *,
    slot_name: str,
    branch_to_delete: str | None,
    close_all: bool,
    pr_info: tuple[int, str] | None,
    plan_info: tuple[int, PlanState] | None,
) -> None:
    """Display the operations that will be performed.

    Args:
        slot_name: Name of the slot being unassigned
        branch_to_delete: Branch name to delete, or None if no branch deletion
        close_all: Whether -a/--all flag was passed
        pr_info: Tuple of (PR number, state) if found, None otherwise
        plan_info: Tuple of (plan number, state) if found, None otherwise
    """
    user_output(click.style("📋 Planning to perform the following operations:", bold=True))
    slot_text = click.style(slot_name, fg="cyan")
    step = 1
    user_output(f"  {step}. 🔓 Unassign slot: {slot_text}")

    if close_all and branch_to_delete:
        step += 1
        pr_text = _format_pr_plan_text(pr_info, "PR")
        user_output(f"  {step}. 🔒 {pr_text}")
        step += 1
        plan_text = _format_plan_text(plan_info)
        user_output(f"  {step}. 📝 {plan_text}")

    if branch_to_delete:
        step += 1
        branch_text = click.style(branch_to_delete, fg="yellow")
        user_output(f"  {step}. 🌳 Delete branch: {branch_text}")


def _format_pr_plan_text(pr_info: tuple[int, str] | None, item_type: str) -> str:
    """Format PR info for display in planning phase."""
    if pr_info is None:
        return f"Close associated {item_type} (if any)"

    number, state = pr_info
    if state == "OPEN":
        return f"Close {item_type} #{number} (currently open)"
    elif state == "MERGED":
        state_text = click.style("merged", fg="green")
        return f"{item_type} #{number} already {state_text}"
    else:
        state_text = click.style("closed", fg="yellow")
        return f"{item_type} #{number} already {state_text}"


def _format_plan_text(plan_info: tuple[int, PlanState] | None) -> str:
    """Format plan info for display in planning phase."""
    if plan_info is None:
        return "Close associated plan (if any)"

    pr_number, state = plan_info
    if state == PlanState.OPEN:
        return f"Close plan #{pr_number} (currently open)"
    else:
        state_text = click.style("closed", fg="yellow")
        return f"Plan #{pr_number} already {state_text}"


def _confirm_operations(ctx: ErkContext, *, force: bool, dry_run: bool) -> bool:
    """Prompt for confirmation unless force or dry-run mode.

    Returns True if operations should proceed, False if aborted.
    """
    if force or dry_run:
        return True

    user_output()
    if not ctx.console.confirm("Proceed with these operations?", default=True):
        user_output(click.style("⭕ Aborted.", fg="red", bold=True))
        return False

    return True


@click.command("unassign")
@click.argument("worktree", metavar="WORKTREE", required=False)
@click.option("-b", "--branch", is_flag=True, help="Delete the branch after unassigning.")
@click.option(
    "-a",
    "--all",
    "close_all",
    is_flag=True,
    help="Delete branch, close associated PR and plan (implies --branch).",
)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would happen without executing.",
)
@click.pass_obj
def slot_unassign(
    ctx: ErkContext,
    worktree: str | None,
    *,
    branch: bool,
    close_all: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Remove a branch assignment from a pool slot.

    WORKTREE is the slot name (e.g., erk-slot-01).

    If no argument is provided, the current pool slot is detected from the
    working directory.

    The worktree directory is kept for reuse with future assignments.

    With `-b/--branch`, also deletes the branch after unassigning.

    With `-a/--all`, deletes branch + closes associated PR + closes plan (implies --branch).

    With `-f/--force`, skips the confirmation prompt.

    With `--dry-run`, shows what would happen without executing.

    Examples:
        erk slot unassign erk-slot-01    # Unassign by worktree name
        erk slot unassign                # Unassign current slot (from within pool worktree)
        erk slot unassign -b             # Unassign + delete branch
        erk slot unassign erk-slot-01 -a # Unassign + close PR + close plan + delete branch
    """
    if dry_run:
        ctx = create_context(dry_run=True)

    # --all implies --branch
    if close_all:
        branch = True

    repo = discover_repo_context(ctx, ctx.cwd)

    # Load pool state
    state = load_pool_state(repo.pool_json_path)
    if state is None:
        user_output("Error: No pool configured. Run `erk branch create` first.")
        raise SystemExit(1) from None

    # Find the assignment to remove
    assignment: SlotAssignment | None = None

    if worktree is not None:
        # Find by slot name
        assignment = _find_assignment_by_slot(state, worktree)
        if assignment is None:
            user_output(
                f"Error: No worktree found for '{worktree}'.\n"
                "Run `erk slot list` to see current assignments."
            )
            raise SystemExit(1) from None
    else:
        # Detect current slot from cwd
        assignment = _find_assignment_by_cwd(state, ctx.cwd)
        if assignment is None:
            user_output(
                "Error: Not inside a pool slot. Specify worktree name.\n"
                "Usage: erk slot unassign WORKTREE"
            )
            raise SystemExit(1) from None

    # Determine branch to delete (if requested)
    branch_to_delete: str | None = None
    if branch:
        worktrees = ctx.git.worktree.list_worktrees(repo.root)
        worktree_branch = get_worktree_branch(worktrees, assignment.worktree_path)
        if worktree_branch is None:
            user_output(
                f"Warning: Slot {assignment.slot_name} is in detached HEAD state. "
                "Cannot delete branch."
            )
        else:
            branch_to_delete = worktree_branch

    # Fetch PR/plan info before displaying plan (for informative planning output)
    pr_info: tuple[int, str] | None = None
    plan_info: tuple[int, PlanState] | None = None
    if close_all and branch_to_delete:
        pr_info = get_pr_info_for_branch(ctx, repo.root, branch_to_delete)
        plan_info = get_plan_info_for_worktree(ctx, repo.root, assignment.slot_name)

    # Display planned operations if flags are present
    if branch or close_all:
        _display_planned_operations(
            slot_name=assignment.slot_name,
            branch_to_delete=branch_to_delete,
            close_all=close_all,
            pr_info=pr_info,
            plan_info=plan_info,
        )

        if not _confirm_operations(ctx, force=force, dry_run=dry_run):
            return

    # Execute the unassign operation
    result = execute_unassign(ctx, repo, state, assignment)

    user_output(
        click.style("✓ ", fg="green")
        + f"Unassigned {click.style(result.branch_name, fg='yellow')} "
        + f"from {click.style(result.slot_name, fg='cyan')}"
    )

    # Execute cleanup operations if requested
    if close_all and branch_to_delete:
        # Close PR for the branch (if exists and open)
        close_pr_for_branch(ctx, repo.root, branch_to_delete)
        # Close plan for the worktree (if exists and open)
        close_plan_for_worktree(ctx, repo.root, assignment.slot_name)

    if branch_to_delete:
        # Delete branch (force=True since user already confirmed)
        delete_branch(
            ctx,
            repo_root=repo.root,
            branch=branch_to_delete,
            force=True,
            dry_run=dry_run,
        )

    if not branch and not close_all:
        user_output("  Switched to placeholder branch")
        user_output("  Tip: Use 'erk wt co root' to return to root worktree")
