"""Branch delete command - delete a branch with worktree-aware cleanup."""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.commands.completions import complete_branch_names
from erk.cli.commands.navigation_helpers import find_assignment_by_worktree_path
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.cli.commands.wt.delete_cmd import (
    _close_plan_for_worktree,
    _close_pr_for_branch,
    _delete_branch_at_error_boundary,
    _escape_worktree_if_inside,
    _get_plan_info_for_worktree,
    _get_pr_info_for_branch,
    _prune_worktrees_safe,
    _try_git_worktree_delete,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import SlotAssignment, load_pool_state
from erk.core.worktree_utils import find_worktree_with_branch
from erk_shared.output.output import user_confirm, user_output
from erk_shared.plan_store.types import PlanState


@dataclass(frozen=True)
class BranchWorktreeInfo:
    """Result of checking worktree association for a branch."""

    worktree_path: Path | None
    slot_assignment: SlotAssignment | None

    @property
    def is_slot(self) -> bool:
        """Return True if the branch is in a slot worktree."""
        return self.slot_assignment is not None

    @property
    def has_worktree(self) -> bool:
        """Return True if the branch has an associated worktree."""
        return self.worktree_path is not None


def get_branch_worktree_info(
    ctx: ErkContext,
    repo: RepoContext,
    branch: str,
) -> BranchWorktreeInfo:
    """Determine if/how a branch is associated with a worktree.

    Args:
        ctx: Erk context with git operations
        repo: Repository context
        branch: Branch name to check

    Returns:
        BranchWorktreeInfo with worktree path and slot assignment info
    """
    worktrees = ctx.git.list_worktrees(repo.root)
    worktree_path = find_worktree_with_branch(worktrees, branch)

    slot_assignment: SlotAssignment | None = None
    if worktree_path is not None:
        state = load_pool_state(repo.pool_json_path)
        if state is not None:
            slot_assignment = find_assignment_by_worktree_path(state, worktree_path)

    return BranchWorktreeInfo(
        worktree_path=worktree_path,
        slot_assignment=slot_assignment,
    )


def _validate_branch_for_deletion(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
) -> None:
    """Validate that the branch can be deleted.

    Args:
        ctx: Erk context with git operations
        repo_root: Repository root directory
        branch: Branch name to validate

    Raises:
        SystemExit: If branch doesn't exist or is a protected trunk branch
    """
    # Check branch exists
    local_branches = ctx.git.list_local_branches(repo_root)
    Ensure.invariant(
        branch in local_branches,
        f"Branch '{branch}' does not exist.",
    )

    # Protect trunk branches
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)
    Ensure.invariant(
        branch != trunk_branch,
        f"Cannot delete trunk branch '{trunk_branch}'.",
    )


def _display_branch_delete_plan(
    *,
    branch: str,
    wt_info: BranchWorktreeInfo,
    close_all: bool,
    pr_info: tuple[int, str] | None,
    plan_info: tuple[int, PlanState] | None,
) -> None:
    """Display the operations that will be performed.

    Args:
        branch: Branch name being deleted
        wt_info: Worktree association info
        close_all: Whether -a/--all flag was passed
        pr_info: Tuple of (PR number, state) if found, None otherwise
        plan_info: Tuple of (plan number, state) if found, None otherwise
    """
    user_output(click.style("📋 Planning to perform the following operations:", bold=True))
    step = 1

    if wt_info.is_slot:
        assert wt_info.slot_assignment is not None
        slot_text = click.style(wt_info.slot_assignment.slot_name, fg="cyan")
        user_output(f"  {step}. 🔓 Unassign slot: {slot_text} (keep worktree for reuse)")
        step += 1
    elif wt_info.has_worktree:
        assert wt_info.worktree_path is not None
        worktree_text = click.style(str(wt_info.worktree_path), fg="cyan")
        user_output(f"  {step}. 🗑️  Delete worktree: {worktree_text}")
        step += 1

    if close_all:
        pr_text = _format_pr_text(pr_info)
        user_output(f"  {step}. 🔒 {pr_text}")
        step += 1
        if wt_info.has_worktree:
            plan_text = _format_plan_text(plan_info)
            user_output(f"  {step}. 📝 {plan_text}")
            step += 1

    branch_text = click.style(branch, fg="yellow")
    user_output(f"  {step}. 🌳 Delete branch: {branch_text}")


def _format_pr_text(pr_info: tuple[int, str] | None) -> str:
    """Format PR info for display in planning phase."""
    if pr_info is None:
        return "Close associated PR (if any)"

    number, state = pr_info
    if state == "OPEN":
        return f"Close PR #{number} (currently open)"
    elif state == "MERGED":
        state_text = click.style("merged", fg="green")
        return f"PR #{number} already {state_text}"
    else:
        state_text = click.style("closed", fg="yellow")
        return f"PR #{number} already {state_text}"


def _format_plan_text(plan_info: tuple[int, PlanState] | None) -> str:
    """Format plan info for display in planning phase."""
    if plan_info is None:
        return "Close associated plan (if any)"

    number, state = plan_info
    if state == PlanState.OPEN:
        return f"Close plan #{number} (currently open)"
    else:
        state_text = click.style("closed", fg="yellow")
        return f"Plan #{number} already {state_text}"


def _confirm_branch_delete(force: bool, dry_run: bool) -> bool:
    """Prompt for confirmation unless force or dry-run mode.

    Returns True if operations should proceed, False if aborted.
    """
    if force or dry_run:
        return True

    user_output()
    if not user_confirm("Proceed with these operations?", default=True):
        user_output(click.style("⭕ Aborted.", fg="red", bold=True))
        return False

    return True


def _handle_slot_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    wt_info: BranchWorktreeInfo,
) -> None:
    """Handle deletion for a slot worktree: unassign slot, keep directory.

    Args:
        ctx: Erk context
        repo: Repository context
        wt_info: Worktree info with slot assignment
    """
    assert wt_info.slot_assignment is not None

    state = load_pool_state(repo.pool_json_path)
    assert state is not None  # Must exist since we found the assignment

    execute_unassign(ctx, repo, state, wt_info.slot_assignment)
    user_output(
        click.style("✓", fg="green")
        + f" Unassigned slot {click.style(wt_info.slot_assignment.slot_name, fg='cyan')}"
    )


def _handle_vanilla_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    wt_info: BranchWorktreeInfo,
    dry_run: bool,
) -> ErkContext:
    """Handle deletion for a vanilla (non-slot) worktree: delete worktree.

    Args:
        ctx: Erk context
        repo: Repository context
        wt_info: Worktree info
        dry_run: If True, don't perform actual deletion

    Returns:
        Potentially updated context (if directory changed)
    """
    assert wt_info.worktree_path is not None

    # Escape if we're inside the worktree being deleted
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    ctx = _escape_worktree_if_inside(ctx, main_repo_root, wt_info.worktree_path, dry_run)

    if dry_run:
        user_output(f"[DRY RUN] Would delete worktree: {wt_info.worktree_path}")
        return ctx

    # Try git worktree remove first
    _try_git_worktree_delete(ctx.git, repo.root, wt_info.worktree_path)

    # Prune worktree metadata
    _prune_worktrees_safe(ctx.git, repo.root)

    worktree_text = click.style(str(wt_info.worktree_path), fg="green")
    user_output(f"✅ Deleted worktree: {worktree_text}")
    return ctx


def _delete_branch(
    ctx: ErkContext,
    *,
    branch: str,
    force: bool,
    close_all: bool,
    dry_run: bool,
) -> None:
    """Internal function to delete a branch with worktree awareness.

    Args:
        ctx: Erk context with git operations
        branch: Name of the branch to delete
        force: Skip confirmation prompts and use -D for branch deletion
        close_all: Also close associated PR and plan
        dry_run: Print what would be done without executing
    """
    if dry_run:
        ctx = create_context(dry_run=True)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Validate the branch can be deleted
    _validate_branch_for_deletion(ctx, repo.root, branch)

    # Get worktree association info
    wt_info = get_branch_worktree_info(ctx, repo, branch)

    # Fetch PR/plan info for display
    pr_info: tuple[int, str] | None = None
    plan_info: tuple[int, PlanState] | None = None
    worktree_name: str | None = None

    if close_all:
        pr_info = _get_pr_info_for_branch(ctx, repo.root, branch)
        if wt_info.has_worktree:
            assert wt_info.worktree_path is not None
            worktree_name = wt_info.worktree_path.name
            plan_info = _get_plan_info_for_worktree(ctx, repo.root, worktree_name)

    # Display planned operations
    _display_branch_delete_plan(
        branch=branch,
        wt_info=wt_info,
        close_all=close_all,
        pr_info=pr_info,
        plan_info=plan_info,
    )

    # Confirm with user
    if not _confirm_branch_delete(force, dry_run):
        return

    # Execute operations in order:
    # 1. Handle worktree (if any)
    if wt_info.is_slot:
        _handle_slot_worktree(ctx, repo, wt_info)
    elif wt_info.has_worktree:
        ctx = _handle_vanilla_worktree(ctx, repo, wt_info, dry_run)

    # 2. Close PR and plan (if --all)
    if close_all:
        _close_pr_for_branch(ctx, repo.root, branch)
        if worktree_name is not None:
            _close_plan_for_worktree(ctx, repo.root, worktree_name)

    # 3. Delete the branch
    _delete_branch_at_error_boundary(
        ctx,
        repo_root=repo.root,
        branch=branch,
        force=True,  # User already confirmed
        dry_run=dry_run,
        graphite=ctx.graphite,
    )


@click.command("delete")
@click.argument("branch", metavar="BRANCH", shell_complete=complete_branch_names)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompts.")
@click.option(
    "-a",
    "--all",
    "close_all",
    is_flag=True,
    help="Also close associated PR and plan.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print what would be done without executing.",
)
@click.pass_obj
def branch_delete(
    ctx: ErkContext,
    *,
    branch: str,
    force: bool,
    close_all: bool,
    dry_run: bool,
) -> None:
    """Delete a branch and clean up its worktree.

    Handles three scenarios based on worktree association:

    \b
    1. Slot worktree: Unassigns the slot (keeps directory for reuse), deletes branch
    2. Vanilla worktree: Prompts to delete both worktree and branch
    3. No worktree: Deletes the branch directly

    With `-f/--force`, skips the confirmation prompt.

    With `-a/--all`, also closes the associated PR and plan (if any).

    Examples:

    \b
        erk branch delete feature-x       # Delete branch (prompts if worktree exists)
        erk br delete feature-x -f        # Delete without confirmation
        erk br delete feature-x -a        # Delete and close PR/plan
    """
    _delete_branch(ctx, branch=branch, force=force, close_all=close_all, dry_run=dry_run)
