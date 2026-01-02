"""Move branches between worktrees with explicit source specification."""

from pathlib import Path

import click

from erk.cli.commands.completions import complete_worktree_names
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_utils import (
    MoveOperationType,
    determine_move_operation,
    find_worktree_containing_path,
    find_worktree_with_branch,
    get_worktree_branch,
)
from erk_shared.output.output import user_confirm, user_output


def _resolve_current_worktree(ctx: ErkContext, repo_root: Path) -> Path:
    """Find worktree containing current directory.

    Raises SystemExit if not in a git repository or not in any worktree.
    """
    Ensure.not_none(ctx.git.get_git_common_dir(ctx.cwd), "Not in a git repository")

    cwd = ctx.cwd.resolve()
    worktrees = ctx.git.list_worktrees(repo_root)
    wt_path = find_worktree_containing_path(worktrees, cwd)
    if wt_path is None:
        user_output(
            f"Error: Current directory ({cwd}) is not in any worktree.\n"
            f"Either run this from within a worktree, or use --worktree or "
            f"--branch to specify the source."
        )
        raise SystemExit(1)
    return wt_path


def resolve_source_worktree(
    ctx: ErkContext,
    repo_root: Path,
    *,
    current: bool,
    branch: str | None,
    worktree: str | None,
    worktrees_dir: Path,
) -> Path:
    """Determine source worktree from flags.

    Defaults to current worktree if no flags provided.
    Raises SystemExit if multiple flags specified or if source cannot be resolved.
    """
    # Count how many source flags are specified
    flag_count = sum([current, branch is not None, worktree is not None])

    if flag_count > 1:
        user_output("Error: Only one of --current, --branch, or --worktree can be specified")
        raise SystemExit(1)

    if flag_count == 0 or current:
        # Default to current worktree (either no flags or --current explicitly set)
        return _resolve_current_worktree(ctx, repo_root)

    if branch:
        # Find worktree containing this branch
        worktrees = ctx.git.list_worktrees(repo_root)
        wt = Ensure.not_none(
            find_worktree_with_branch(worktrees, branch),
            f"Branch '{branch}' not found in any worktree",
        )
        return wt

    if worktree:
        # Resolve worktree name to path
        wt_path = worktree_path_for(worktrees_dir, worktree)
        # Validate that the worktree exists
        Ensure.path_exists(ctx, wt_path, f"Worktree '{worktree}' does not exist")
        return wt_path

    user_output("Error: Invalid state - no source specified")
    raise SystemExit(1)


def detect_operation_type(
    source_wt: Path, target_wt: Path, ctx: ErkContext, repo_root: Path
) -> MoveOperationType:
    """Determine whether to move, swap, or create based on target existence.

    Returns MoveOperationType enum value.
    """
    worktrees = ctx.git.list_worktrees(repo_root)
    operation = determine_move_operation(worktrees, source_wt, target_wt)
    return operation.operation_type


def execute_move(
    ctx: ErkContext,
    repo_root: Path,
    source_wt: Path,
    target_wt: Path,
    fallback_ref: str,
    *,
    force: bool,
) -> None:
    """Execute move operation (target doesn't exist or is in detached HEAD).

    Moves the branch from source to target, then switches source to fallback_ref.
    """
    # Validate source has a branch
    worktrees = ctx.git.list_worktrees(repo_root)
    source_branch = Ensure.not_none(
        get_worktree_branch(worktrees, source_wt), "Source worktree is in detached HEAD state"
    )

    # Check for uncommitted changes in source
    if ctx.git.has_uncommitted_changes(source_wt) and not force:
        user_output(
            f"Error: Uncommitted changes in source worktree '{source_wt.name}'.\n"
            f"Commit, stash, or use --force to override."
        )
        raise SystemExit(1)

    target_exists = ctx.git.path_exists(target_wt)

    # To move branch from source to target, we need to avoid having the same branch
    # checked out in two places simultaneously. Strategy:
    # 1. Detach HEAD in source worktree (frees up source_branch)
    # 2. Create/checkout source_branch in target worktree
    # 3. Checkout fallback_ref in source worktree
    user_output(f"Moving '{source_branch}' from '{source_wt.name}' to '{target_wt.name}'")
    ctx.git.checkout_detached(source_wt, source_branch)

    if target_exists:
        # Target exists - check for uncommitted changes
        if ctx.git.has_uncommitted_changes(target_wt) and not force:
            user_output(
                f"Error: Uncommitted changes in target worktree '{target_wt.name}'.\n"
                f"Commit, stash, or use --force to override."
            )
            raise SystemExit(1)

        # Checkout branch in existing target
        ctx.git.checkout_branch(target_wt, source_branch)
    else:
        # Create new worktree with branch
        ctx.git.add_worktree(
            repo_root, target_wt, branch=source_branch, ref=None, create_branch=False
        )

    # Check if fallback_ref is already checked out elsewhere, and detach it if needed
    fallback_wt = ctx.git.is_branch_checked_out(repo_root, fallback_ref)
    if fallback_wt is not None and fallback_wt.resolve() != source_wt.resolve():
        # Fallback branch is checked out in another worktree, detach it first
        ctx.git.checkout_detached(fallback_wt, fallback_ref)

    # Switch source to fallback branch
    ctx.git.checkout_branch(source_wt, fallback_ref)

    user_output(f"✓ Moved '{source_branch}' from '{source_wt.name}' to '{target_wt.name}'")


def execute_swap(
    ctx: ErkContext,
    repo_root: Path,
    source_wt: Path,
    target_wt: Path,
    *,
    force: bool,
) -> None:
    """Execute swap operation (both worktrees exist with branches).

    Swaps the branches between source and target worktrees.
    """
    worktrees = ctx.git.list_worktrees(repo_root)
    source_branch = get_worktree_branch(worktrees, source_wt)
    target_branch = get_worktree_branch(worktrees, target_wt)

    if source_branch is None or target_branch is None:
        user_output("Error: Both worktrees must have branches checked out for swap")
        raise SystemExit(1)

    # Check for uncommitted changes
    if ctx.git.has_uncommitted_changes(source_wt) or ctx.git.has_uncommitted_changes(target_wt):
        if not force:
            user_output(
                "Error: Uncommitted changes detected in one or more worktrees.\n"
                "Commit, stash, or use --force to override."
            )
            raise SystemExit(1)

    # Confirm swap unless --force
    if not force:
        user_output("This will swap branches between worktrees:")
        user_output(f"  '{source_wt.name}': '{source_branch}' → '{target_branch}'")
        user_output(f"  '{target_wt.name}': '{target_branch}' → '{source_branch}'")
        if not user_confirm("Continue?", default=False):
            user_output("Swap cancelled")
            raise SystemExit(0)

    user_output(f"Swapping branches between '{source_wt.name}' and '{target_wt.name}'")

    # To swap branches between worktrees, we need to avoid having the same branch
    # checked out in two places simultaneously. Strategy:
    # 1. Detach HEAD in source worktree (frees up source_branch)
    # 2. Checkout source_branch in target worktree
    # 3. Checkout target_branch in source worktree
    ctx.git.checkout_detached(source_wt, source_branch)
    ctx.git.checkout_branch(target_wt, source_branch)
    ctx.git.checkout_branch(source_wt, target_branch)

    user_output(f"✓ Swapped '{source_branch}' ↔ '{target_branch}'")


@click.command("move")
@click.option("--current", is_flag=True, help="Use current worktree as source")
@click.option("--branch", help="Auto-detect worktree containing this branch")
@click.option("--worktree", help="Use specific worktree as source")
@click.option("--ref", default="main", help="Fallback branch for source after move (default: main)")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompts")
@click.argument("target", required=True, shell_complete=complete_worktree_names)
@click.pass_obj
def move_stack(
    ctx: ErkContext,
    current: bool,
    branch: str | None,
    worktree: str | None,
    ref: str,
    force: bool,
    target: str,
) -> None:
    """Move branches between worktrees with explicit source specification.

    Examples:

        \b
        # Move current branch back to repository root
        erk move root

        \b
        # Move from current worktree to new worktree
        erk move target-wt

        \b
        # Move from current worktree (explicit)
        erk move --current target-wt

        \b
        # Auto-detect source from branch name
        erk move --branch feature-x new-wt

        \b
        # Move from specific source to target
        erk move --worktree old-wt new-wt

        \b
        # Swap branches between current and another worktree
        erk move --current existing-wt

        \b
        # Force operation without prompts (for scripts)
        erk move --current target-wt --force

        \b
        # Specify custom fallback branch
        erk move --current new-wt --ref develop
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Resolve source worktree
    source_wt = resolve_source_worktree(
        ctx,
        repo.root,
        current=current,
        branch=branch,
        worktree=worktree,
        worktrees_dir=repo.worktrees_dir,
    )

    # Resolve target worktree path
    # Special case: "root" refers to the main repository root (not current worktree)
    if target == "root":
        # main_repo_root is always set by RepoContext.__post_init__, but ty doesn't know
        target_wt = repo.main_repo_root if repo.main_repo_root else repo.root
    else:
        target_wt = worktree_path_for(repo.worktrees_dir, target)

    # Validate source and target are different
    if source_wt.resolve() == target_wt.resolve():
        user_output("Error: Source and target worktrees are the same")
        raise SystemExit(1)

    # Detect operation type
    operation_type = detect_operation_type(source_wt, target_wt, ctx, repo.root)

    # Execute operation
    if operation_type == MoveOperationType.SWAP:
        execute_swap(ctx, repo.root, source_wt, target_wt, force=force)
    else:
        # Auto-detect default branch if using 'main' default and it doesn't exist
        if ref == "main":
            detected_default = ctx.git.detect_trunk_branch(repo.root)
            ref = detected_default

        execute_move(ctx, repo.root, source_wt, target_wt, ref, force=force)
