import shutil
import subprocess
from pathlib import Path

import click
from erk_shared.git.abc import Git
from erk_shared.output.output import user_output

from erk.cli.commands.completions import complete_worktree_names
from erk.cli.core import (
    discover_repo_context,
    validate_worktree_name_for_deletion,
    worktree_path_for,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, create_context, regenerate_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_utils import (
    find_worktree_containing_path,
    get_worktree_branch,
)


def _try_git_worktree_delete(git_ops: Git, repo_root: Path, wt_path: Path) -> bool:
    """Attempt git worktree remove, returning success status.

    This function violates LBYL norms because there's no reliable way to
    check a priori if git worktree remove will succeed. The worktree might be:
    - Already removed from git metadata
    - In a partially corrupted state
    - Referenced by stale lock files

    Git's own error handling is unreliable for these edge cases, so we use
    try/except as an error boundary and rely on manual cleanup + prune.

    Returns:
        True if git removal succeeded, False otherwise
    """
    try:
        git_ops.remove_worktree(repo_root, wt_path, force=True)
        return True
    except Exception:
        # Git removal failed - manual cleanup will handle it
        return False


def _prune_worktrees_safe(git_ops: Git, repo_root: Path) -> None:
    """Prune worktree metadata, ignoring errors if nothing to prune.

    This function violates LBYL norms because git worktree prune can fail
    for various reasons (no stale worktrees, permission issues, etc.) that
    are not easily detectable beforehand. Since pruning is a cleanup operation
    and failure doesn't affect the primary operation, we allow silent failure.
    """
    try:
        git_ops.prune_worktrees(repo_root)
    except Exception:
        # Prune might fail if there's nothing to prune or other non-critical issues
        pass


def _escape_worktree_if_inside(
    ctx: ErkContext, repo_root: Path, wt_path: Path, dry_run: bool
) -> ErkContext:
    """Change to repository root if currently inside the worktree being deleted.

    Prevents the shell from being left in a deleted directory. Returns a new
    context if directory was changed (context is immutable), otherwise returns
    the original context.
    """
    if not ctx.git.path_exists(ctx.cwd):
        return ctx

    current_dir = ctx.cwd.resolve()
    worktrees = ctx.git.list_worktrees(repo_root)
    current_worktree_path = find_worktree_containing_path(worktrees, current_dir)

    if current_worktree_path is None:
        return ctx

    if current_worktree_path.resolve() != wt_path.resolve():
        return ctx

    # Change to repository root before deletion
    user_output(
        click.style("ℹ️  ", fg="blue", bold=True)
        + f"Changing directory to repository root: {click.style(str(repo_root), fg='cyan')}"
    )

    # Change directory using safe_chdir which handles both real and sentinel paths
    if not dry_run and ctx.git.safe_chdir(repo_root):
        # Regenerate context with new cwd (context is immutable)
        return regenerate_context(ctx)

    return ctx


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


def _display_planned_operations(wt_path: Path, branch_to_delete: str | None) -> None:
    """Display the operations that will be performed."""
    user_output(click.style("📋 Planning to perform the following operations:", bold=True))
    worktree_text = click.style(str(wt_path), fg="cyan")
    user_output(f"  1. 🗑️  Delete worktree: {worktree_text}")
    if branch_to_delete:
        branch_text = click.style(branch_to_delete, fg="yellow")
        user_output(f"  2. 🌳 Delete branch: {branch_text}")


def _confirm_operations(force: bool, dry_run: bool) -> bool:
    """Prompt for confirmation unless force or dry-run mode.

    Returns True if operations should proceed, False if aborted.
    """
    if force or dry_run:
        return True

    prompt_text = click.style("Proceed with these operations?", fg="yellow", bold=True)
    if not click.confirm(f"\n{prompt_text}", default=True, err=True):
        user_output(click.style("⭕ Aborted.", fg="red", bold=True))
        return False

    return True


def _delete_worktree_directory(ctx: ErkContext, repo_root: Path, wt_path: Path) -> None:
    """Delete the worktree directory from filesystem.

    First attempts git worktree remove, then manually deletes if still present.
    This function encapsulates the legitimate error boundary for shutil.rmtree
    because in pure test mode, the path may be a sentinel that doesn't exist
    on the real filesystem.
    """
    # Try to delete via git first - this updates git's metadata when possible
    _try_git_worktree_delete(ctx.git, repo_root, wt_path)

    # Always manually delete directory if it still exists
    if not ctx.git.path_exists(wt_path):
        return

    if ctx.dry_run:
        user_output(f"[DRY RUN] Would delete directory: {wt_path}")
        return

    # Only call shutil.rmtree() if we're on a real filesystem.
    # In pure test mode, we skip the actual deletion since it's a sentinel path.
    # This violates LBYL because there's no reliable way to distinguish sentinel
    # paths from real paths that have been deleted between the path_exists check
    # and the rmtree call (race condition).
    try:
        shutil.rmtree(wt_path)
    except OSError:
        # Path doesn't exist on real filesystem (sentinel path), skip deletion
        pass

    # Prune worktree metadata to clean up any stale references
    _prune_worktrees_safe(ctx.git, repo_root)


def _delete_branch_at_error_boundary(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    force: bool,
    dry_run: bool,
) -> None:
    """Delete a branch after its worktree has been removed.

    This function encapsulates a legitimate error boundary because:
    1. `gt delete` prompts for user confirmation, which can be declined (exit 1)
    2. `git branch -d` may fail if branch is not fully merged
    3. There's no LBYL way to predict user's response to interactive prompt
    4. This is a CLI error boundary - appropriate place per AGENTS.md

    The exception handling distinguishes between user-declined (expected) and
    actual errors (propagated as SystemExit).

    Note: run_subprocess_with_context catches CalledProcessError and re-raises
    as RuntimeError with the original exception in __cause__.
    """
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    try:
        if use_graphite:
            ctx.git.delete_branch_with_graphite(repo_root, branch, force=force)
        else:
            ctx.git.delete_branch(repo_root, branch, force=force)
        if not dry_run:
            branch_text = click.style(branch, fg="green")
            user_output(f"✅ Deleted branch: {branch_text}")
    except RuntimeError as e:
        _handle_branch_deletion_error(e, branch, force)


def _handle_branch_deletion_error(e: RuntimeError, branch: str, force: bool) -> None:
    """Handle errors from branch deletion commands.

    This function encapsulates the error boundary logic for branch deletion.
    Exit code 1 with --force off typically means user declined the confirmation
    prompt, which is expected behavior. Other errors are propagated as SystemExit.

    Args:
        e: RuntimeError from run_subprocess_with_context, with the original
           CalledProcessError accessible via e.__cause__
        branch: Name of the branch that failed to delete
        force: Whether --force flag was used
    """
    branch_text = click.style(branch, fg="yellow")

    # Extract returncode from the original CalledProcessError in __cause__
    returncode: int | None = None
    if isinstance(e.__cause__, subprocess.CalledProcessError):
        returncode = e.__cause__.returncode

    if returncode == 1 and not force:
        # User declined - this is expected behavior, not an error
        user_output(f"⭕ Skipped deletion of branch: {branch_text} (user declined or not eligible)")
    else:
        # Other error (branch doesn't exist, git failure, etc.)
        # The RuntimeError message already contains stderr from run_subprocess_with_context
        user_output(
            click.style("Error: ", fg="red") + f"Failed to delete branch {branch_text}: {e}"
        )
        raise SystemExit(1) from e


def _delete_worktree(
    ctx: ErkContext,
    name: str,
    force: bool,
    delete_branch: bool,
    dry_run: bool,
    quiet: bool = False,
) -> None:
    """Internal function to delete a worktree.

    Args:
        ctx: Erk context with git operations
        name: Name of the worktree to delete
        force: Skip confirmation prompts and use -D for branch deletion
        delete_branch: Delete the branch checked out on the worktree
        dry_run: Print what would be done without executing destructive operations
        quiet: Suppress planning output (still shows final confirmation)
    """
    if dry_run:
        ctx = create_context(dry_run=True)

    validate_worktree_name_for_deletion(name)

    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")

    # main_repo_root is always set by RepoContext.__post_init__, but pyright doesn't know
    main_repo = repo.main_repo_root if repo.main_repo_root else repo.root
    ctx = _escape_worktree_if_inside(ctx, main_repo, wt_path, dry_run)

    branch_to_delete: str | None = None
    if delete_branch:
        branch_to_delete = _collect_branch_to_delete(ctx, repo.root, wt_path, name)

    if not quiet:
        _display_planned_operations(wt_path, branch_to_delete)

    if not _confirm_operations(force, dry_run):
        return

    _delete_worktree_directory(ctx, repo.root, wt_path)

    if branch_to_delete:
        # User already confirmed via _confirm_operations(), so force=True for branch deletion
        # to avoid redundant Graphite prompt
        _delete_branch_at_error_boundary(
            ctx, repo.root, branch_to_delete, force=True, dry_run=dry_run
        )

    if not dry_run:
        path_text = click.style(str(wt_path), fg="green")
        user_output(f"✅ {path_text}")


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
    "--dry-run",
    is_flag=True,
    # dry_run=False: Allow destructive operations by default
    default=False,
    help="Print what would be done without executing destructive operations.",
)
@click.pass_obj
def delete_wt(ctx: ErkContext, name: str, force: bool, branch: bool, dry_run: bool) -> None:
    """Delete the worktree directory.

    With `-f/--force`, skips the confirmation prompt and uses -D for branch deletion.
    Attempts `git worktree remove` before deleting the directory.
    """
    _delete_worktree(ctx, name, force, branch, dry_run)
