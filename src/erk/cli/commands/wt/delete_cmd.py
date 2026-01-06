from pathlib import Path

import click

from erk.cli.commands.completions import complete_worktree_names
from erk.cli.commands.deletion_helpers import (
    close_plan_for_worktree,
    close_pr_for_branch,
    delete_branch_at_error_boundary,
    delete_worktree_directory,
    escape_worktree_if_inside,
    get_plan_info_for_worktree,
    get_pr_info_for_branch,
)
from erk.cli.commands.navigation_helpers import check_pending_extraction_marker
from erk.cli.core import (
    discover_repo_context,
    validate_worktree_name_for_deletion,
    worktree_path_for,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_utils import get_worktree_branch
from erk_shared.output.output import user_confirm, user_output
from erk_shared.plan_store.types import PlanState


def _collect_branch_to_delete(
    ctx: ErkContext, repo_root: Path, wt_path: Path, name: str
) -> str | None:
    """Get the branch checked out on the worktree, if any.

    Returns the branch name, or None if in detached HEAD state.
    """
    worktrees = ctx.git.list_worktrees(repo_root)
    worktree_branch = get_worktree_branch(worktrees, wt_path)

    if worktree_branch is None:
        user_output(
            f"Warning: Worktree {name} is in detached HEAD state. Cannot delete branch.",
        )
        return None

    return worktree_branch


def _display_planned_operations(
    *,
    wt_path: Path,
    branch_to_delete: str | None,
    close_all: bool,
    pr_info: tuple[int, str] | None,
    plan_info: tuple[int, PlanState] | None,
) -> None:
    """Display the operations that will be performed.

    Args:
        wt_path: Path to the worktree being deleted
        branch_to_delete: Branch name to delete, or None if detached HEAD
        close_all: Whether -a/--all flag was passed
        pr_info: Tuple of (PR number, state) if found, None otherwise
        plan_info: Tuple of (plan number, state) if found, None otherwise
    """
    user_output(click.style("📋 Planning to perform the following operations:", bold=True))
    worktree_text = click.style(str(wt_path), fg="cyan")
    step = 1
    user_output(f"  {step}. 🗑️  Delete worktree: {worktree_text}")

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

    number, state = plan_info
    if state == PlanState.OPEN:
        return f"Close plan #{number} (currently open)"
    else:
        state_text = click.style("closed", fg="yellow")
        return f"Plan #{number} already {state_text}"


def _confirm_operations(force: bool, dry_run: bool) -> bool:
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


def _delete_worktree(
    ctx: ErkContext,
    *,
    name: str,
    force: bool,
    delete_branch: bool,
    dry_run: bool,
    quiet: bool,
    close_all: bool,
) -> None:
    """Internal function to delete a worktree.

    Args:
        ctx: Erk context with git operations
        name: Name of the worktree to delete
        force: Skip confirmation prompts and use -D for branch deletion
        delete_branch: Delete the branch checked out on the worktree
        dry_run: Print what would be done without executing destructive operations
        quiet: Suppress planning output (still shows final confirmation)
        close_all: Also close associated PR and plan
    """
    if dry_run:
        ctx = create_context(dry_run=True)

    validate_worktree_name_for_deletion(name)

    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")

    # Check for pending extraction marker
    check_pending_extraction_marker(wt_path, force)

    # main_repo_root is always set by RepoContext.__post_init__, but ty doesn't know
    main_repo = repo.main_repo_root if repo.main_repo_root else repo.root
    ctx = escape_worktree_if_inside(ctx, main_repo, wt_path, dry_run)

    branch_to_delete: str | None = None
    if delete_branch:
        branch_to_delete = _collect_branch_to_delete(ctx, repo.root, wt_path, name)

    # Fetch PR/plan info before displaying plan (for informative planning output)
    pr_info: tuple[int, str] | None = None
    plan_info: tuple[int, PlanState] | None = None
    if close_all and branch_to_delete:
        pr_info = get_pr_info_for_branch(ctx, repo.root, branch_to_delete)
        plan_info = get_plan_info_for_worktree(ctx, repo.root, name)

    if not quiet:
        _display_planned_operations(
            wt_path=wt_path,
            branch_to_delete=branch_to_delete,
            close_all=close_all,
            pr_info=pr_info,
            plan_info=plan_info,
        )

    if not _confirm_operations(force, dry_run):
        return

    # Order of operations: worktree delete → PR close → plan close → branch delete
    was_slot = delete_worktree_directory(ctx, repo, wt_path)

    if close_all and branch_to_delete:
        # Close PR for the branch (if exists and open)
        close_pr_for_branch(ctx, repo.root, branch_to_delete)
        # Close plan for the worktree (if exists and open)
        close_plan_for_worktree(ctx, repo.root, name)

    if branch_to_delete:
        # User already confirmed via _confirm_operations(), so force=True for branch deletion
        # to avoid redundant Graphite prompt
        delete_branch_at_error_boundary(
            ctx,
            repo_root=repo.root,
            branch=branch_to_delete,
            force=True,
            dry_run=dry_run,
            graphite=ctx.graphite,
        )

    if not dry_run and not was_slot:
        # Only show "Deleted worktree" message if not a slot (slot shows its own message)
        path_text = click.style(str(wt_path), fg="green")
        user_output(f"✅ Deleted worktree: {path_text}")


@click.command("delete")
@click.argument("name", metavar="NAME", shell_complete=complete_worktree_names)
@click.option("-f", "--force", is_flag=True, help="Do not prompt for confirmation.")
@click.option(
    "-b",
    "--branch",
    is_flag=True,
    help="Delete the branch checked out on the worktree.",
)
@click.option(
    "-a",
    "--all",
    "close_all",  # Use different name to avoid shadowing builtin
    is_flag=True,
    help="Delete branch, close associated PR and plan.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    # dry_run=False: Allow destructive operations by default
    default=False,
    help="Print what would be done without executing destructive operations.",
)
@click.pass_obj
def delete_wt(
    ctx: ErkContext, *, name: str, force: bool, branch: bool, close_all: bool, dry_run: bool
) -> None:
    """Delete the worktree directory.

    With `-f/--force`, skips the confirmation prompt and uses -D for branch deletion.
    Attempts `git worktree remove` before deleting the directory.

    With `-a/--all`, also closes the associated PR and plan (implies --branch).
    """
    # --all implies --branch
    if close_all:
        branch = True
    _delete_worktree(
        ctx,
        name=name,
        force=force,
        delete_branch=branch,
        dry_run=dry_run,
        quiet=False,
        close_all=close_all,
    )
