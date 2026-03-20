"""Unified land command for PRs.

This command merges a PR and cleans up the worktree/branch.
It accepts a branch name, PR number, or PR URL as argument.

Usage:
    erk land              # Land current branch's PR
    erk land --stack      # Land the current Graphite stack
    erk land 123          # Land PR by number
    erk land <url>        # Land PR by URL
    erk land <branch>     # Land PR for branch
"""

import re
from dataclasses import dataclass, replace
from enum import Enum, auto
from pathlib import Path
from typing import Literal, NamedTuple, assert_never

import click

from erk.cli.activation import print_temp_script_instructions, render_activation_script
from erk.cli.commands.checkout_helpers import ensure_branch_has_worktree
from erk.cli.commands.land_pipeline import (
    LandError,
    make_execution_state,
    make_initial_state,
    run_execution_pipeline,
    run_validation_pipeline,
)
from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
)
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    run_objective_update_after_land,
)
from erk.cli.commands.wt.delete_cmd import _prune_worktrees_safe
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.ensure_ideal import EnsureIdeal
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    load_pool_state,
)
from erk.core.worktree_utils import is_root_worktree
from erk_shared.gateway.console.real import InteractiveConsole
from erk_shared.gateway.github.types import PRDetails
from erk_shared.output.output import machine_output, user_output
from erk_shared.stack.validation import validate_parent_is_trunk
from erk_slots.common import (
    extract_slot_number,
    find_branch_assignment,
    get_placeholder_branch_name,
)
from erk_slots.unassign_cmd import execute_unassign


@dataclass(frozen=True)
class LandTarget:
    """Resolved landing target from any entry point.

    Carries all resolved state needed to land a PR, regardless of how
    the target was specified (current branch, PR number, or branch name).
    """

    branch: str
    pr_details: PRDetails
    worktree_path: Path | None
    is_current_branch: bool
    use_graphite: bool
    target_child_branch: str | None  # Only set for --up mode


@dataclass(frozen=True)
class CleanupContext:
    """Carries cleanup state through the extraction process.

    This dataclass bundles all parameters needed for cleanup operations,
    enabling focused helper functions without parameter explosion.
    """

    ctx: ErkContext
    repo: RepoContext
    branch: str
    worktree_path: Path | None
    main_repo_root: Path
    script: bool
    pull_flag: bool
    force: bool
    is_current_branch: bool
    target_child_branch: str | None
    no_delete: bool
    skip_activation_output: bool
    cleanup_confirmed: bool  # Pre-gathered from validation phase


@dataclass(frozen=True)
class CleanupConfirmation:
    """Pre-gathered cleanup confirmation result.

    Captures user's response to cleanup prompt during validation phase,
    allowing all confirmations to be batched upfront before any mutations.
    """

    proceed: bool  # True = proceed with cleanup, False = preserve


class CleanupType(Enum):
    """Classification of cleanup scenario after PR merge."""

    NO_DELETE = auto()
    NO_WORKTREE = auto()
    SLOT_ASSIGNED = auto()
    SLOT_UNASSIGNED = auto()
    NON_SLOT = auto()
    ROOT_WORKTREE = auto()


@dataclass(frozen=True)
class ResolvedCleanup:
    """Result of classifying the cleanup scenario.

    Carries the enum variant plus optional resolved state for the
    SLOT_ASSIGNED variant (avoids re-resolving pool state after classification).
    """

    cleanup_type: CleanupType
    pool_state: PoolState | None
    assignment: SlotAssignment | None


def determine_cleanup_type(
    *,
    no_delete: bool,
    worktree_path: Path | None,
    pool_json_path: Path,
    branch: str,
    repo_root: Path,
) -> ResolvedCleanup:
    """Classify the cleanup scenario for a landed branch.

    Mirrors the dispatch logic in _cleanup_and_navigate but returns an explicit
    enum variant instead of branching inline. Pure classification — no side effects.
    """
    if no_delete:
        return ResolvedCleanup(
            cleanup_type=CleanupType.NO_DELETE,
            pool_state=None,
            assignment=None,
        )

    if worktree_path is None:
        return ResolvedCleanup(
            cleanup_type=CleanupType.NO_WORKTREE,
            pool_state=None,
            assignment=None,
        )

    state = load_pool_state(pool_json_path)
    assignment = find_branch_assignment(state, branch) if state is not None else None

    if assignment is not None:
        return ResolvedCleanup(
            cleanup_type=CleanupType.SLOT_ASSIGNED,
            pool_state=state,
            assignment=assignment,
        )

    if extract_slot_number(worktree_path.name) is not None:
        return ResolvedCleanup(
            cleanup_type=CleanupType.SLOT_UNASSIGNED,
            pool_state=state,
            assignment=None,
        )

    if is_root_worktree(worktree_path, repo_root):
        return ResolvedCleanup(
            cleanup_type=CleanupType.ROOT_WORKTREE,
            pool_state=state,
            assignment=None,
        )

    return ResolvedCleanup(
        cleanup_type=CleanupType.NON_SLOT,
        pool_state=state,
        assignment=None,
    )


def _gather_cleanup_confirmation(
    ctx: ErkContext,
    *,
    target: LandTarget,
    repo: RepoContext,
    force: bool,
) -> CleanupConfirmation:
    """Gather cleanup confirmation upfront during validation.

    Uses determine_cleanup_type() to classify the cleanup scenario,
    then prompts based on the classification. Returns result for
    threading through to cleanup functions.

    This consolidates all cleanup-related confirmation prompts into
    the validation phase, before any mutations occur.
    """
    if force or ctx.dry_run:
        return CleanupConfirmation(proceed=True)

    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    resolved = determine_cleanup_type(
        no_delete=False,  # no_delete handled separately in _handle_no_delete
        worktree_path=target.worktree_path,
        pool_json_path=repo.pool_json_path,
        branch=target.branch,
        repo_root=main_repo_root,
    )

    match resolved.cleanup_type:
        case CleanupType.NO_DELETE | CleanupType.NO_WORKTREE:
            # No confirmation needed
            return CleanupConfirmation(proceed=True)
        case CleanupType.SLOT_ASSIGNED:
            assert resolved.assignment is not None
            proceed = ctx.console.confirm(
                f"After landing, unassign slot '{resolved.assignment.slot_name}' "
                f"and delete branch '{target.branch}'?",
                default=True,
            )
        case CleanupType.SLOT_UNASSIGNED:
            assert target.worktree_path is not None
            user_output(
                click.style("Warning:", fg="yellow")
                + f" Slot '{target.worktree_path.name}' has no assignment "
                + "(branch checked out outside erk)."
            )
            user_output("  Use `erk pr co` or `erk slot checkout` to track slot usage.")
            proceed = ctx.console.confirm(
                f"After landing, release slot '{target.worktree_path.name}' "
                f"and delete branch '{target.branch}'?",
                default=True,
            )
        case CleanupType.ROOT_WORKTREE:
            proceed = ctx.console.confirm(
                f"After landing, delete branch '{target.branch}'?",
                default=True,
            )
        case CleanupType.NON_SLOT:
            assert target.worktree_path is not None
            proceed = ctx.console.confirm(
                f"After landing, delete branch '{target.branch}'"
                f" and remove worktree '{target.worktree_path.name}'?",
                default=True,
            )
        case _:
            assert_never(resolved.cleanup_type)

    return CleanupConfirmation(proceed=proceed)


def _ensure_branch_not_checked_out(
    ctx: ErkContext,
    *,
    repo_root: Path,
    branch: str,
) -> Path | None:
    """Ensure branch is not checked out in any worktree.

    If the branch is checked out in a worktree, checkout detached HEAD
    at trunk to release the branch for deletion.

    This is a defensive check to handle scenarios where:
    - Pool state has a stale worktree_path that doesn't match the actual worktree
    - execute_unassign() checked out a placeholder in the wrong location
    - Any other scenario where the branch remains checked out

    Args:
        ctx: ErkContext
        repo_root: Repository root path
        branch: Branch name to check

    Returns:
        Path of the worktree where branch was found and detached, or None
        if branch was not checked out anywhere.
    """
    worktree_path = ctx.git.worktree.find_worktree_for_branch(repo_root, branch)
    if worktree_path is None:
        return None

    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    ctx.branch_manager.checkout_detached(worktree_path, trunk_branch)
    return worktree_path


def _handle_no_delete(cleanup: CleanupContext) -> None:
    """Handle --no-delete flag: preserve branch and slot, optionally navigate."""
    user_output(
        click.style("✓", fg="green")
        + f" Branch '{cleanup.branch}' and slot assignment preserved (--no-delete)"
    )
    if cleanup.is_current_branch:
        _navigate_after_land(
            cleanup.ctx,
            repo=cleanup.repo,
            script=cleanup.script,
            pull_flag=cleanup.pull_flag,
            target_child_branch=cleanup.target_child_branch,
            skip_activation_output=cleanup.skip_activation_output,
        )
    else:
        raise SystemExit(0)


def _cleanup_no_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup when no worktree exists: delete branch only if exists locally."""
    local_branches = cleanup.ctx.git.branch.list_local_branches(cleanup.main_repo_root)
    if cleanup.branch in local_branches:
        _ensure_branch_not_checked_out(
            cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
        )
        cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch, force=True)
        user_output(click.style("✓", fg="green") + f" Deleted branch '{cleanup.branch}'")
    # else: Branch doesn't exist locally - no cleanup needed (remote implementation or fork PR)


def _cleanup_slot_with_assignment(
    cleanup: CleanupContext,
    *,
    state: PoolState,
    assignment: SlotAssignment,
) -> None:
    """Handle cleanup for slot worktree with assignment: unassign and delete branch."""
    if not cleanup.cleanup_confirmed:
        user_output("Slot preserved. Branch still exists locally.")
        return
    execute_unassign(cleanup.ctx, cleanup.repo, state, assignment)
    # Defensive: ensure branch is released before deletion
    # (handles stale pool state where worktree_path doesn't match actual location)
    _ensure_branch_not_checked_out(
        cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
    )
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch, force=True)
    user_output(click.style("✓", fg="green") + " Unassigned slot and deleted branch")


def _cleanup_slot_without_assignment(
    cleanup: CleanupContext,
    *,
    slot_name: str,
) -> None:
    """Handle cleanup for slot worktree without assignment: checkout placeholder, delete branch."""
    if not cleanup.cleanup_confirmed:
        user_output("Slot preserved. Branch still exists locally.")
        return

    # Checkout placeholder branch before deleting the feature branch
    # worktree_path is guaranteed non-None since we're in a slot worktree
    assert cleanup.worktree_path is not None
    placeholder = get_placeholder_branch_name(slot_name)
    if placeholder is not None:
        # Force-update placeholder to trunk so the slot starts fresh
        cleanup.ctx.git.branch.create_branch(
            cleanup.main_repo_root,
            placeholder,
            cleanup.ctx.git.branch.detect_trunk_branch(cleanup.main_repo_root),
            force=True,
        )
        cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, placeholder)

    # Defensive: ensure branch is released before deletion
    _ensure_branch_not_checked_out(
        cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
    )
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch, force=True)
    user_output(click.style("✓", fg="green") + " Released slot and deleted branch")


def _cleanup_root_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup for root worktree: delete branch, skip worktree removal."""
    assert cleanup.worktree_path is not None

    if not cleanup.cleanup_confirmed:
        user_output("Branch preserved.")
        return

    trunk = cleanup.ctx.git.branch.detect_trunk_branch(cleanup.main_repo_root)
    cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, trunk)

    _ensure_branch_not_checked_out(
        cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
    )
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch, force=True)
    user_output(click.style("✓", fg="green") + " Deleted branch (root worktree preserved)")


def _cleanup_non_slot_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup for non-slot worktree: delete branch and remove worktree."""
    # worktree_path is guaranteed non-None since we're in a non-slot worktree
    assert cleanup.worktree_path is not None

    # Check for uncommitted changes before switching branches
    Ensure.invariant(
        not cleanup.ctx.git.status.has_uncommitted_changes(cleanup.worktree_path),
        f"Worktree has uncommitted changes at {cleanup.worktree_path}.\n"
        "Commit or stash your changes before landing.",
    )

    if not cleanup.cleanup_confirmed:
        user_output("Branch and worktree preserved.")
        return

    # Checkout detached HEAD at trunk before deleting feature branch
    # (git won't delete a branch that's checked out in any worktree)
    # Use detached HEAD instead of checkout_branch because trunk may already
    # be checked out in the root worktree
    trunk_branch = cleanup.ctx.git.branch.detect_trunk_branch(cleanup.main_repo_root)
    cleanup.ctx.branch_manager.checkout_detached(cleanup.worktree_path, trunk_branch)

    # Defensive: verify checkout succeeded before deletion
    _ensure_branch_not_checked_out(
        cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
    )
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch, force=True)

    # Escape process cwd out of worktree before removal
    # (git worktree remove fails if cwd is inside the target)
    cleanup.ctx.git.worktree.safe_chdir(cleanup.main_repo_root)

    # Remove the worktree directory — non-slot worktrees have no useful state
    # after branch deletion (unlike slot worktrees which have placeholder branches)
    worktree_name = cleanup.worktree_path.name
    if not cleanup.force:
        proceed = cleanup.ctx.console.confirm(
            f"Remove worktree directory '{worktree_name}'?",
            default=True,
        )
        if not proceed:
            user_output(f"Worktree '{worktree_name}' preserved (branch already deleted).")
            return
    cleanup.ctx.git.worktree.remove_worktree(
        cleanup.main_repo_root, cleanup.worktree_path, force=True
    )
    _prune_worktrees_safe(cleanup.ctx.git, cleanup.main_repo_root)

    user_output(
        click.style("✓", fg="green") + f" Deleted branch and removed worktree '{worktree_name}'"
    )


def _navigate_or_exit(cleanup: CleanupContext) -> None:
    """Handle navigation or exit after cleanup.

    In dry-run mode, shows summary and exits.
    Otherwise, navigates to appropriate location or outputs no-op script.
    """
    # In dry-run mode, skip navigation and show summary
    if cleanup.ctx.dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Navigate (only if we were in the deleted worktree)
    if cleanup.is_current_branch:
        _navigate_after_land(
            cleanup.ctx,
            repo=cleanup.repo,
            script=cleanup.script,
            pull_flag=cleanup.pull_flag,
            target_child_branch=cleanup.target_child_branch,
            skip_activation_output=cleanup.skip_activation_output,
        )
    else:
        if cleanup.script:
            # Output no-op script for shell integration consistency
            script_content = render_activation_script(
                worktree_path=cleanup.ctx.cwd,
                target_subpath=None,
                post_cd_commands=None,
                final_message='echo "Land complete"',
                comment="land complete (no navigation needed)",
            )
            result = cleanup.ctx.script_writer.write_activation_script(
                script_content,
                command_name="land",
                comment="no-op",
            )
            machine_output(str(result.path), nl=False)
        raise SystemExit(0)


def _cleanup_landed_branch(cleanup: CleanupContext) -> None:
    """Run the appropriate cleanup path without navigation or exit behavior."""
    resolved = determine_cleanup_type(
        no_delete=cleanup.no_delete,
        worktree_path=cleanup.worktree_path,
        pool_json_path=cleanup.repo.pool_json_path,
        branch=cleanup.branch,
        repo_root=cleanup.main_repo_root,
    )

    match resolved.cleanup_type:
        case CleanupType.NO_DELETE:
            user_output(
                click.style("✓", fg="green")
                + f" Branch '{cleanup.branch}' and slot assignment preserved (--no-delete)"
            )
        case CleanupType.NO_WORKTREE:
            _cleanup_no_worktree(cleanup)
        case CleanupType.SLOT_ASSIGNED:
            assert resolved.pool_state is not None
            assert resolved.assignment is not None
            _cleanup_slot_with_assignment(
                cleanup,
                state=resolved.pool_state,
                assignment=resolved.assignment,
            )
        case CleanupType.SLOT_UNASSIGNED:
            assert cleanup.worktree_path is not None
            _cleanup_slot_without_assignment(cleanup, slot_name=cleanup.worktree_path.name)
        case CleanupType.ROOT_WORKTREE:
            _cleanup_root_worktree(cleanup)
        case CleanupType.NON_SLOT:
            _cleanup_non_slot_worktree(cleanup)
        case _:
            assert_never(resolved.cleanup_type)


class ParsedArgument(NamedTuple):
    """Result of parsing a land command argument."""

    arg_type: Literal["pr-number", "pr-url", "branch"]
    pr_number: int | None


def parse_argument(arg: str) -> ParsedArgument:
    """Parse argument to determine type.

    Args:
        arg: The argument string (PR number, PR URL, or branch name)

    Returns:
        ParsedArgument with:
        - arg_type="pr-number", pr_number=N if arg is a numeric PR number
        - arg_type="pr-url", pr_number=N if arg is a GitHub or Graphite PR URL
        - arg_type="branch", pr_number=None if arg is a branch name
    """
    # Try parsing as a plain number (PR number)
    if arg.isdigit():
        return ParsedArgument(arg_type="pr-number", pr_number=int(arg))

    # Try parsing as a GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
    match = re.search(r"/pull/(\d+)", arg)
    if match:
        return ParsedArgument(arg_type="pr-url", pr_number=int(match.group(1)))

    # Try parsing as a Graphite PR URL (e.g., https://app.graphite.com/github/pr/owner/repo/123)
    match = re.search(r"/pr/[^/]+/[^/]+/(\d+)", arg)
    if match:
        return ParsedArgument(arg_type="pr-url", pr_number=int(match.group(1)))

    # Treat as branch name
    return ParsedArgument(arg_type="branch", pr_number=None)


def resolve_branch_for_pr(ctx: ErkContext, repo_root: Path, pr_details: PRDetails) -> str:
    """Resolve the local branch name for a PR.

    For same-repo PRs, returns the head branch name.
    For fork PRs, returns "pr/{pr_number}" (the checkout convention).

    Args:
        ctx: ErkContext
        repo_root: Repository root directory
        pr_details: PR details from GitHub

    Returns:
        Local branch name to use for this PR
    """
    if pr_details.is_cross_repository:
        # Fork PR - local checkout uses pr/{number} naming convention
        return f"pr/{pr_details.number}"
    return pr_details.head_ref_name


def check_unresolved_comments(
    ctx: ErkContext,
    repo_root: Path,
    pr_number: int,
    *,
    force: bool,
) -> None:
    """Check for unresolved review threads and prompt if any exist.

    Args:
        ctx: ErkContext
        repo_root: Repository root directory
        pr_number: PR number to check
        force: If True, skip confirmation prompt

    Raises:
        SystemExit(0) if user declines to continue
        SystemExit(1) if non-interactive and has unresolved comments without --force
    """
    # Handle rate limit errors gracefully - this is an advisory check.
    # We cannot LBYL for rate limits (no way to check quota before calling),
    # so try/except is the appropriate pattern here.
    try:
        threads = ctx.github.get_pr_review_threads(repo_root, pr_number, include_resolved=False)
    except RuntimeError as e:
        error_str = str(e)
        if "RATE_LIMIT" in error_str or "rate limit" in error_str.lower():
            user_output(
                click.style("⚠ ", fg="yellow")
                + "Could not check for unresolved comments (API rate limited)"
            )
            return  # Continue without blocking
        raise  # Re-raise other errors

    if threads and not force:
        user_output(
            click.style("⚠ ", fg="yellow")
            + f"PR #{pr_number} has {len(threads)} unresolved review comment(s)."
        )
        Ensure.invariant(
            ctx.console.is_stdin_interactive(),
            "Cannot prompt for confirmation in non-interactive mode.\n"
            + "Use --force to skip this check.",
        )
        if not ctx.console.confirm("Continue anyway?", default=False):
            raise SystemExit(0)


def _validate_pr_for_landing(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    target: LandTarget,
    force: bool,
    script: bool,
) -> CleanupConfirmation:
    """Validate PR is ready to land - shared validation for all entry points.

    This function consolidates validation steps that happen after PR resolution:
    1. Clean working tree (if landing current branch)
    2. PR state is OPEN
    3. PR base is trunk (for non-Graphite paths; Graphite validates via stack)
    4. Unresolved comments check
    5. Learn status check (for plan branches)
    6. Cleanup confirmation (batched upfront)

    Args:
        ctx: ErkContext
        repo: Repository context
        target: Resolved landing target
        force: If True, skip confirmation prompts
        script: If True, output no-op activation script on abort

    Returns:
        CleanupConfirmation with user's pre-gathered response

    Raises:
        SystemExit(1) on validation failure
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # 1. Clean working tree check (only for current branch)
    if target.is_current_branch:
        check_clean_working_tree(ctx)

    # 2. PR state is OPEN
    pr_number = target.pr_details.number
    Ensure.invariant(
        target.pr_details.state == "OPEN",
        f"Pull request #{pr_number} is not open (state: {target.pr_details.state}).\n"
        f"PR #{pr_number} has already been {target.pr_details.state.lower()}.",
    )

    # 3. PR base is trunk (skip for Graphite - it validates via stack)
    if not target.use_graphite:
        trunk = ctx.git.branch.detect_trunk_branch(main_repo_root)
        Ensure.invariant(
            target.pr_details.base_ref_name == trunk,
            f"PR #{pr_number} targets '{target.pr_details.base_ref_name}' "
            + f"but should target '{trunk}'.\n\n"
            + "The GitHub PR's base branch has diverged from your local stack.\n"
            + "Run: gt restack && gt submit\n"
            + f"Then retry: erk land {target.branch}",
        )

    # 4. Unresolved comments check
    check_unresolved_comments(ctx, main_repo_root, pr_number, force=force)

    # 5. Gather cleanup confirmation upfront (all confirms batched before mutations)
    return _gather_cleanup_confirmation(ctx, target=target, repo=repo, force=force)


def _resolve_land_target_current_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    up_flag: bool,
) -> LandTarget:
    """Resolve landing target when landing current branch.

    Validates Graphite stack for current branch and handles --up preconditions.

    Args:
        ctx: ErkContext
        repo: Repository context
        up_flag: Whether --up flag was passed

    Returns:
        LandTarget with resolved branch, PR, and navigation target

    Raises:
        SystemExit(1) on validation failure
    """
    # Check clean working tree FIRST (before any other validation)
    check_clean_working_tree(ctx)

    # Get current branch
    current_branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    current_worktree_path = Ensure.not_none(
        ctx.git.worktree.find_worktree_for_branch(repo.root, current_branch),
        f"Cannot find worktree for current branch '{current_branch}'.",
    )

    # Validate --up preconditions BEFORE any mutations (fail-fast)
    target_child_branch: str | None = None
    if up_flag:
        # --up requires Graphite for child branch tracking
        Ensure.invariant(
            ctx.branch_manager.is_graphite_managed(),
            "--up flag requires Graphite for child branch tracking.\n\n"
            + "To enable Graphite: erk config set use_graphite true\n\n"
            + "Without --up, erk land will navigate to trunk after landing.",
        )

        children = Ensure.truthy(
            ctx.branch_manager.get_child_branches(repo.root, current_branch),
            f"Cannot use --up: branch '{current_branch}' has no children.\n"
            "Use 'erk land' without --up to return to trunk.",
        )
        children_list = ", ".join(f"'{c}'" for c in children)
        Ensure.invariant(
            len(children) == 1,
            f"Cannot use --up: branch '{current_branch}' has multiple children: "
            f"{children_list}.\n"
            "Use 'erk land' without --up, then 'erk co <branch>' to choose.",
        )
        target_child_branch = children[0]

    # Validate branch is landable via Graphite stack (if Graphite managed)
    use_graphite = ctx.branch_manager.is_graphite_managed()
    if use_graphite:
        parent = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
        trunk = ctx.git.branch.detect_trunk_branch(repo.root)
        validation_error = validate_parent_is_trunk(
            current_branch=current_branch,
            parent_branch=parent,
            trunk_branch=trunk,
        )
        Ensure.invariant(
            validation_error is None,
            validation_error.message if validation_error else "",
        )

    # Look up PR for current branch
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    pr_details = EnsureIdeal.unwrap_pr(
        ctx.github.get_pr_for_branch(main_repo_root, current_branch),
        f"No pull request found for branch '{current_branch}'.",
    )

    return LandTarget(
        branch=current_branch,
        pr_details=pr_details,
        worktree_path=current_worktree_path,
        is_current_branch=True,
        use_graphite=use_graphite,
        target_child_branch=target_child_branch,
    )


def _resolve_land_target_pr(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    pr_number: int,
    up_flag: bool,
) -> LandTarget:
    """Resolve landing target when landing by PR number.

    Fetches PR by number, resolves branch name (handles forks), rejects --up.

    Args:
        ctx: ErkContext
        repo: Repository context
        pr_number: PR number to land
        up_flag: Whether --up flag was passed (rejected for PR landing)

    Returns:
        LandTarget with resolved branch, PR, and navigation target

    Raises:
        SystemExit(1) on validation failure
    """
    # Validate --up is not used with PR argument
    Ensure.invariant(
        not up_flag,
        "Cannot use --up when specifying a PR.\n"
        "The --up flag only works when landing the current branch's PR.",
    )

    # Fetch PR details
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    pr_details = EnsureIdeal.unwrap_pr(
        ctx.github.get_pr(main_repo_root, pr_number),
        f"Pull request #{pr_number} not found.",
    )

    # Resolve branch name (handles fork PRs)
    branch = resolve_branch_for_pr(ctx, main_repo_root, pr_details)

    # Determine if we're in the target branch's worktree
    current_branch = ctx.git.branch.get_current_branch(ctx.cwd)
    is_current_branch = current_branch == branch

    # Check if worktree exists for this branch
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)

    return LandTarget(
        branch=branch,
        pr_details=pr_details,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        use_graphite=False,  # Specific PR landing uses GitHub API directly
        target_child_branch=None,  # No --up for specific PR
    )


def _resolve_land_target_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    branch_name: str,
) -> LandTarget:
    """Resolve landing target when landing by branch name.

    Looks up PR by branch name, determines worktree.

    Args:
        ctx: ErkContext
        repo: Repository context
        branch_name: Branch name to land

    Returns:
        LandTarget with resolved branch, PR, and navigation target

    Raises:
        SystemExit(1) on validation failure
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Look up PR for branch
    pr_details = EnsureIdeal.unwrap_pr(
        ctx.github.get_pr_for_branch(main_repo_root, branch_name),
        f"No pull request found for branch '{branch_name}'.",
    )

    # Determine if we're in the target branch's worktree
    current_branch = ctx.git.branch.get_current_branch(ctx.cwd)
    is_current_branch = current_branch == branch_name

    # Check if worktree exists for this branch
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch_name)

    return LandTarget(
        branch=branch_name,
        pr_details=pr_details,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        use_graphite=False,  # Branch landing uses GitHub API directly
        target_child_branch=None,  # No --up for branch landing
    )


def _execute_land_directly(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    target: LandTarget,
    script: bool,
    pull_flag: bool,
    no_delete: bool,
    skip_learn: bool,
    cleanup_confirmed: bool,
) -> None:
    """Execute land directly without generating a deferred script.

    This is the default path when neither --up nor --down is passed.
    Merges the PR and cleans up the branch inline without navigation.

    Args:
        ctx: ErkContext
        repo: Repository context
        target: Resolved landing target
        script: Whether running in script mode
        pull_flag: Whether to pull after landing
        no_delete: Preserve branch after landing
        skip_learn: Skip creating a learn plan after landing
        cleanup_confirmed: Whether user confirmed cleanup during validation
    """
    branch = target.branch
    pr_number = target.pr_details.number

    # Handle dry-run mode
    if ctx.dry_run:
        user_output(f"Would merge PR #{pr_number} for branch '{branch}'")
        user_output(f"Would delete branch '{branch}'")
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Capture plan context BEFORE execution pipeline (which deletes the branch)
    pr_id = ctx.plan_backend.resolve_pr_number_for_branch(main_repo_root, branch)
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch)

    # Build execution state and run the pipeline directly
    state = make_execution_state(
        cwd=ctx.cwd,
        pr_number=pr_number,
        branch=branch,
        worktree_path=target.worktree_path,
        is_current_branch=target.is_current_branch,
        use_graphite=target.use_graphite,
        pull_flag=pull_flag,
        no_delete=no_delete,
        no_cleanup=not cleanup_confirmed,
        script=script,
        target_child_branch=None,
        pr_id=pr_id,
        skip_learn=skip_learn,
    )

    # Re-derive main_repo_root from discovery
    state = replace(state, main_repo_root=main_repo_root)

    # Run execution pipeline (merge + cleanup)
    exit_after: SystemExit | None = None
    try:
        result = run_execution_pipeline(ctx, state)
        if isinstance(result, LandError):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
    except SystemExit as exc:
        if exc.code != 0:
            raise
        exit_after = exc

    # Objective update (fail-open — merge already succeeded)
    if objective_number is not None:
        run_objective_update_after_land(
            ctx,
            objective=objective_number,
            pr=pr_number,
            branch=branch,
            worktree_path=main_repo_root,
        )

    # Determine navigation target — if worktree was removed, navigate to root repo
    nav_target = ctx.cwd
    if target.worktree_path is not None and target.is_current_branch:
        if not ctx.git.worktree.path_exists(target.worktree_path):
            nav_target = main_repo_root

    # In script mode, output script path for shell wrapper compatibility
    if script:
        script_content = render_activation_script(
            worktree_path=nav_target,
            target_subpath=None,
            post_cd_commands=None,
            final_message='echo "Land complete"',
            comment="land complete (direct execution, no navigation)",
        )
        script_result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="land",
            comment="no-op",
        )
        machine_output(str(script_result.path), nl=False)

    if exit_after is not None:
        raise exit_after

    raise SystemExit(0)


def _land_target(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    target: LandTarget,
    script: bool,
    force: bool,
    pull_flag: bool,
    no_delete: bool,
    skip_learn: bool,
    cleanup_confirmed: bool,
    down_flag: bool,
) -> None:
    """Generate execution script after validation pipeline has completed.

    Called when --up or --down is passed (navigation mode). Produces a deferred
    execution script that must be sourced to navigate the shell.

    Validation and confirmation gathering are done by run_validation_pipeline()
    before this function is called. This function handles:
    1. Look up objective and slot assignment
    2. Determine navigation target path
    3. Handle dry-run mode
    4. Generate and write execution script
    5. Display instructions or output script path

    Args:
        ctx: ErkContext
        repo: Repository context
        target: Resolved landing target
        script: Whether to output machine-readable script path
        force: Skip confirmation prompts
        pull_flag: Whether to pull after landing
        no_delete: Preserve branch after landing
        cleanup_confirmed: Whether user confirmed cleanup during validation
        down_flag: Whether --down flag was passed

    Raises:
        SystemExit(0) after outputting script instructions
        SystemExit(1) on validation failure
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    pr_number = target.pr_details.number
    branch = target.branch

    # Step 1: Look up plan and objective for branch (needed for script generation)
    pr_id = ctx.plan_backend.resolve_pr_number_for_branch(main_repo_root, branch)
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch)

    # Step 2: Look up slot assignment (needed for dry-run output)
    state = load_pool_state(repo.pool_json_path)
    slot_assignment: SlotAssignment | None = None
    if state is not None:
        slot_assignment = find_branch_assignment(state, branch)

    # Step 4: Determine target path for navigation after landing
    if target.target_child_branch is not None:
        # --up mode: navigate to child branch worktree
        target_path = ctx.git.worktree.find_worktree_for_branch(
            main_repo_root, target.target_child_branch
        )
        if target_path is None:
            # Will auto-create worktree in execute phase
            if repo.worktrees_dir:
                target_path = repo.worktrees_dir / target.target_child_branch
            else:
                target_path = main_repo_root
    else:
        # Navigate to trunk/root
        target_path = main_repo_root

    # Step 5: Handle dry-run mode
    if ctx.dry_run:
        user_output(f"Would merge PR #{pr_number} for branch '{branch}'")
        if slot_assignment is not None:
            user_output(f"Would unassign slot '{slot_assignment.slot_name}'")
        user_output(f"Would delete branch '{branch}'")
        user_output(f"Would navigate to {target_path}")
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Step 6: Generate execution script with all pre-validated state
    # Determine worktree_path: use target's worktree if available, else current cwd
    worktree_path = target.worktree_path if target.worktree_path else ctx.cwd
    script_content = render_land_execution_script(
        pr_number=pr_number,
        branch=branch,
        worktree_path=worktree_path,
        is_current_branch=target.is_current_branch,
        objective_number=objective_number,
        learn_source_pr=int(pr_id) if pr_id is not None else None,
        use_graphite=target.use_graphite,
        skip_learn=skip_learn,
        cleanup_confirmed=cleanup_confirmed,
        target_path=target_path,
    )

    # Write script to .erk/bin/land.sh
    result = ctx.script_writer.write_worktree_script(
        script_content,
        worktree_path=worktree_path,
        script_name="land",
        command_name="land",
        comment=f"land {branch}",
    )

    # Step 7: Build display flags and output instructions
    display_flags: list[str] = []
    if force:
        display_flags.append("-f")
    if target.target_child_branch is not None:
        display_flags.append("--up")
    elif down_flag:
        display_flags.append("--down")
    if not pull_flag:
        display_flags.append("--no-pull")
    if no_delete:
        display_flags.append("--no-delete")

    if script:
        # Shell integration mode: output just the path
        machine_output(str(result.path), nl=False)
    else:
        # Interactive mode: show instructions and copy to clipboard
        print_temp_script_instructions(
            result.path,
            instruction="To land the PR:",
            copy=True,
            args=[pr_number, branch],
            extra_flags=display_flags if display_flags else None,
        )
    raise SystemExit(0)


def _cleanup_and_navigate(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    branch: str,
    worktree_path: Path | None,
    script: bool,
    pull_flag: bool,
    force: bool,
    is_current_branch: bool,
    target_child_branch: str | None,
    no_delete: bool,
    skip_activation_output: bool,
    cleanup_confirmed: bool,
) -> None:
    """Handle worktree/branch cleanup and navigation after PR merge.

    This is shared logic used by both current-branch and specific-PR landing.

    Args:
        ctx: ErkContext
        repo: Repository context
        branch: Branch name to clean up
        worktree_path: Path to worktree (None if no worktree exists)
        script: Whether to output activation script
        pull_flag: Whether to pull after landing
        force: Whether to skip cleanup confirmation (legacy, kept for compatibility)
        is_current_branch: True if landing from the branch's worktree
        target_child_branch: Target child branch for --up navigation (None for trunk)
        no_delete: Whether to preserve the branch and slot assignment
        skip_activation_output: If True, skip activation message (used in execute mode
            where the script's cd command handles navigation)
        cleanup_confirmed: Pre-gathered confirmation from validation phase
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    cleanup = CleanupContext(
        ctx=ctx,
        repo=repo,
        branch=branch,
        worktree_path=worktree_path,
        main_repo_root=main_repo_root,
        script=script,
        pull_flag=pull_flag,
        force=force,
        is_current_branch=is_current_branch,
        target_child_branch=target_child_branch,
        no_delete=no_delete,
        skip_activation_output=skip_activation_output,
        cleanup_confirmed=cleanup_confirmed,
    )

    if cleanup.no_delete:
        _handle_no_delete(cleanup)
        return

    _cleanup_landed_branch(cleanup)
    _navigate_or_exit(cleanup)


def _navigate_after_land(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    pull_flag: bool,
    target_child_branch: str | None,
    skip_activation_output: bool,
) -> None:
    """Navigate to appropriate location after landing.

    Args:
        ctx: ErkContext
        repo: Repository context
        script: Whether to output activation script
        pull_flag: Whether to include git pull in activation
        target_child_branch: If set, navigate to this child branch (--up mode)
        skip_activation_output: If True, skip activation message (used in execute mode
            where the script's cd command handles navigation)
    """
    # Create post-deletion repo context with root pointing to main_repo_root
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    post_deletion_repo = replace(repo, root=main_repo_root)

    if target_child_branch is not None:
        # Skip activation output in execute mode (script's cd command handles navigation)
        if skip_activation_output:
            raise SystemExit(0)
        target_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, target_child_branch)
        if target_path is None:
            # Auto-create worktree for child via slot allocation
            target_path, _ = ensure_branch_has_worktree(
                ctx, post_deletion_repo, branch_name=target_child_branch, no_slot=False, force=False
            )
        # Suggest running gt restack --downstack to update child branch's PR base
        # Use --downstack to only restack the current branch, avoiding errors if
        # upstack branches are checked out in other worktrees
        user_output(
            click.style("💡", fg="cyan")
            + f" Run 'gt restack --downstack' in {target_child_branch} to update PR base"
        )
        activate_worktree(
            ctx=ctx,
            repo=post_deletion_repo,
            target_path=target_path,
            script=script,
            command_name="land",
            preserve_relative_path=True,
            post_cd_commands=None,
            source_branch=None,
            force=False,
        )
        # activate_worktree raises SystemExit(0)
    else:
        # Execute git pull in Python (before activation script) to avoid race condition
        # with stale index.lock files from earlier git operations
        if pull_flag:
            trunk_branch = ctx.git.branch.detect_trunk_branch(main_repo_root)

            # Fetch first to get latest remote state
            ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk_branch)

            # Check if local branch can be fast-forwarded
            divergence = ctx.git.branch.is_branch_diverged_from_remote(
                main_repo_root, trunk_branch, "origin"
            )

            if divergence.is_diverged:
                user_output(
                    click.style("Warning: ", fg="yellow")
                    + f"Local {trunk_branch} has diverged from origin/{trunk_branch}.\n"
                    + f"  (local is {divergence.ahead} ahead, {divergence.behind} behind)\n"
                    + "  Skipping pull. To resolve, run:\n"
                    + f"    git fetch origin && git reset --hard origin/{trunk_branch}"
                )
            elif divergence.behind > 0:
                user_output(f"Pulling latest changes from origin/{trunk_branch}...")
                try:
                    ctx.git.remote.pull_branch(main_repo_root, "origin", trunk_branch, ff_only=True)
                except RuntimeError:
                    # Fallback if pull still fails for unexpected reasons
                    user_output(
                        click.style("Warning: ", fg="yellow")
                        + "git pull failed (try running manually)"
                    )
            # If behind == 0, already up to date, no pull needed

        # Skip activation output in execute mode (script's cd command handles navigation)
        if skip_activation_output:
            raise SystemExit(0)

        # Output activation script pointing to trunk/root repo
        activate_root_repo(
            ctx,
            repo=post_deletion_repo,
            script=script,
            command_name="land",
            post_cd_commands=None,
            source_branch=None,
            force=False,
        )
        # activate_root_repo raises SystemExit(0)


def render_land_execution_script(
    *,
    pr_number: int,
    branch: str,
    worktree_path: Path | None,
    is_current_branch: bool,
    objective_number: int | None,
    learn_source_pr: int | None,
    use_graphite: bool,
    skip_learn: bool,
    cleanup_confirmed: bool,
    target_path: Path,
) -> str:
    """Generate shell script that executes land and navigates.

    This script is generated after validation passes. When sourced, it:
    1. Validates required arguments (PR number and branch)
    2. Calls `erk exec land-execute` with pre-validated state plus user flags
    3. If land-execute fails (e.g., merge conflict), stops immediately via ``return 1``
    4. On success, navigates to the target location (trunk or child branch)

    Note: The execute phase always skips confirmation prompts because the user
    already approved by sourcing the script. --force is not passed because
    _execute_land handles this internally.

    The script requires two positional arguments:
    - $1: PR number to merge
    - $2: Branch name being landed

    Additional flags after the positional args (e.g., -f --up --no-pull --no-delete)
    are passed through to `erk exec land-execute` via "$@".

    **Baked-in (static, determined at script generation time):**
    - --worktree-path: worktree location
    - --is-current-branch: whether landing from that worktree
    - --use-graphite: whether Graphite is enabled
    - --no-cleanup: user declined cleanup during validation

    **Objective update (separate command, fail-open):**
    When objective_number is set, a second command line is emitted after
    the land-execute command: ``erk exec objective-update-after-land``.
    This runs without ``|| return 1`` because landing already succeeded.

    **Passed via "$@" (user-controllable flags):**
    - --up: navigate upstack (resolved at execution time)
    - --no-pull: skip pull after landing
    - --no-delete: preserve branch/slot
    - -f: passed for documentation (execute mode is already non-interactive)

    Args:
        pr_number: PR number to merge (not used directly, passed as arg)
        branch: Branch name being landed (not used directly, passed as arg)
        worktree_path: Path to worktree being cleaned up (if any)
        is_current_branch: Whether landing from the branch's own worktree
        objective_number: Linked objective issue number (if any)
        learn_source_pr: Linked PR number for learn issue creation
        use_graphite: Whether to use Graphite for merge
        target_path: Where to cd after land completes

    Returns:
        Shell script content as string
    """
    # Silence unused parameter warnings - these are still needed for the function
    # signature to document what values the script will receive at runtime
    _ = pr_number, branch

    # Build erk exec land-execute command using shell variables for pr/branch
    # Static flags are baked in; user flags come from "$@"
    cmd_parts = ["erk exec land-execute"]
    cmd_parts.append('--pr-number="$PR_NUMBER"')
    cmd_parts.append('--branch="$BRANCH"')
    if worktree_path is not None:
        cmd_parts.append(f"--worktree-path={worktree_path}")
    if is_current_branch:
        cmd_parts.append("--is-current-branch")
    if use_graphite:
        cmd_parts.append("--use-graphite")
    if not cleanup_confirmed:
        cmd_parts.append("--no-cleanup")
    if skip_learn:
        cmd_parts.append("--skip-learn")
    if objective_number is not None:
        cmd_parts.append(f"--objective-number={objective_number}")
    if learn_source_pr is not None:
        cmd_parts.append(f"--linked-pr-number={learn_source_pr}")
    # User-controllable flags passed through "$@"
    cmd_parts.append('"$@"')

    erk_cmd = " ".join(cmd_parts)
    target_path_str = str(target_path)

    return f"""# erk land deferred execution
# Usage: source land.sh <pr_number> <branch> [flags...]
PR_NUMBER="${{1:?Error: PR number required}}"
BRANCH="${{2:?Error: Branch name required}}"
shift 2

{erk_cmd} || return 1
cd {target_path_str}
"""


def _execute_land(
    ctx: ErkContext,
    *,
    pr_number: int | None,
    branch: str | None,
    worktree_path: Path | None,
    is_current_branch: bool,
    target_child_branch: str | None,
    use_graphite: bool,
    pull_flag: bool,
    no_delete: bool,
    no_cleanup: bool,
    script: bool,
    learn_source_pr: int | None,
    skip_learn: bool,
) -> None:
    """Execute deferred land operations from activation script.

    This function is called when `erk land --execute` is invoked by the
    activation script. All validation has already been done - this just
    performs the destructive operations via the execution pipeline.

    Confirmations are skipped in execute mode because the user already approved
    by sourcing the activation script. Confirmations happen during validation
    phase only.

    Args:
        ctx: ErkContext
        pr_number: PR number to merge
        branch: Branch name being landed
        worktree_path: Path to worktree being cleaned up (if any)
        is_current_branch: Whether landing from the branch's own worktree
        target_child_branch: Target child branch for --up navigation
        use_graphite: Whether to use Graphite for merge
        pull_flag: Whether to pull after landing
        no_delete: Whether to preserve branch and slot
        no_cleanup: Whether user declined cleanup during validation
        script: Whether running in script mode
        learn_source_pr: Linked PR number for learn issue creation
    """
    # Validate required parameters
    Ensure.invariant(pr_number is not None, "Missing --exec-pr-number in execute mode")
    Ensure.invariant(branch is not None, "Missing --exec-branch in execute mode")
    # Type narrowing for the type checker (invariants don't narrow types)
    assert pr_number is not None
    assert branch is not None

    state = make_execution_state(
        cwd=ctx.cwd,
        pr_number=pr_number,
        branch=branch,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        use_graphite=use_graphite,
        pull_flag=pull_flag,
        no_delete=no_delete,
        no_cleanup=no_cleanup,
        script=script,
        target_child_branch=target_child_branch,
        pr_id=str(learn_source_pr) if learn_source_pr is not None else None,
        skip_learn=skip_learn,
    )

    # Re-derive main_repo_root from discovery
    repo = discover_repo_context(ctx, ctx.cwd)
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    state = replace(state, main_repo_root=main_repo_root)

    result = run_execution_pipeline(ctx, state)
    if isinstance(result, LandError):
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1)


@click.command("land", cls=CommandWithHiddenOptions)
@script_option
@click.argument("target", required=False)
@click.option(
    "-u",
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.option(
    "-d",
    "--down",
    "down_flag",
    is_flag=True,
    help="Navigate to trunk after landing (produces source command)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip all confirmation prompts (unresolved comments, worktree deletion)",
)
@click.option(
    "--stack",
    "stack_flag",
    is_flag=True,
    hidden=True,
    help="Land the current Graphite stack bottom-up.",
)
@click.option(
    "--pull/--no-pull",
    "pull_flag",
    default=True,
    help="Pull latest changes after landing (default: --pull)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be done without executing destructive operations.",
)
@click.option(
    "--no-delete",
    "no_delete",
    is_flag=True,
    help="Preserve the local branch and its slot assignment after landing.",
)
@click.option(
    "--skip-learn",
    "skip_learn",
    is_flag=True,
    help="Skip creating a learn PR after landing.",
)
@click.pass_obj
def land(
    ctx: ErkContext,
    *,
    script: bool,
    target: str | None,
    up_flag: bool,
    down_flag: bool,
    force: bool,
    stack_flag: bool,
    pull_flag: bool,
    dry_run: bool,
    no_delete: bool,
    skip_learn: bool,
) -> None:
    """Merge PR and clean up branch.

    By default, merges the PR and cleans up the branch directly (no source
    command needed). Use --down to navigate to trunk after landing, or --up
    to navigate to a child branch. Both --down and --up produce a source
    command for shell navigation.

    \b
    Usage:
      erk land              # Merge + cleanup directly (no navigation)
      erk land --stack      # Merge the current Graphite stack bottom-up
      erk land --down       # Merge + cleanup + navigate to trunk
      erk land --up         # Merge + cleanup + navigate to child branch
      erk land 123          # Land PR #123
      erk land <url>        # Land PR by GitHub URL
      erk land <branch>     # Land PR for branch

    Requires:
    - PR must be open and ready to merge
    - PR's base branch must be trunk

    Note: --stack, --up, and --down are mutually exclusive navigation modes.
    --up and --stack require Graphite.
    """
    # Replace context with appropriate wrappers based on flags.
    #
    # Note: Other commands (consolidate, branch checkout) handle --script by skipping
    # confirms entirely with `if not script: confirm(...)`. Land uses context recreation
    # instead because:
    # 1. It has multiple confirms with different defaults that affect behavior
    #    (e.g., unresolved comments defaults to False=abort, branch delete defaults to True)
    # 2. It uses ctx.console.is_stdin_interactive() which needs ScriptConsole to return True
    # ScriptConsole.confirm() honors defaults automatically, preserving correct semantics.
    if dry_run:
        ctx = create_context(dry_run=True)
        script = False  # Force human-readable output in dry-run mode
    elif script and isinstance(ctx.console, InteractiveConsole):
        # Recreate context with script=True for ScriptConsole.
        # Only recreate when InteractiveConsole - preserve FakeConsole for tests.
        ctx = create_context(dry_run=False, script=True)

    Ensure.invariant(
        not (up_flag and down_flag),
        "--up and --down are mutually exclusive.\n"
        "--up navigates to child branch, --down navigates to trunk.",
    )
    Ensure.invariant(
        not (stack_flag and up_flag),
        "--stack and --up are mutually exclusive.\n"
        "--stack lands the full stack, while --up lands one branch and navigates upward.",
    )
    Ensure.invariant(
        not (stack_flag and down_flag),
        "--stack and --down are mutually exclusive.\n"
        "--stack already lands toward trunk and does not support deferred navigation.",
    )
    Ensure.invariant(
        not (stack_flag and target is not None),
        "Cannot use --stack with a PR, URL, or branch argument.\n"
        "--stack only works from the currently checked out branch.",
    )

    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    if stack_flag:
        from erk.cli.commands.land_stack import execute_land_stack

        execute_land_stack(
            ctx,
            repo=repo,
            script=script,
            force=force,
            pull_flag=pull_flag,
            no_delete=no_delete,
            skip_learn=skip_learn,
        )
        return

    # Run validation pipeline (resolve target, validate PR, gather confirmations)
    initial_state = make_initial_state(
        cwd=ctx.cwd,
        force=force,
        script=script,
        pull_flag=pull_flag,
        no_delete=no_delete,
        up_flag=up_flag,
        dry_run=ctx.dry_run,
        skip_learn=skip_learn,
        target_arg=target,
        repo_root=repo.root,
        main_repo_root=main_repo_root,
    )
    result = run_validation_pipeline(ctx, initial_state)

    if isinstance(result, LandError):
        Ensure.invariant(False, result.message)
    # Type narrowing: Ensure.invariant exits on failure, so result is LandState here
    assert not isinstance(result, LandError)
    assert result.pr_details is not None

    land_target = LandTarget(
        branch=result.branch,
        pr_details=result.pr_details,
        worktree_path=result.worktree_path,
        is_current_branch=result.is_current_branch,
        use_graphite=result.use_graphite,
        target_child_branch=result.target_child_branch,
    )

    if up_flag or down_flag:
        # Navigation mode: generate deferred execution script (requires source command)
        _land_target(
            ctx,
            repo=repo,
            target=land_target,
            script=script,
            force=force,
            pull_flag=pull_flag,
            no_delete=no_delete,
            skip_learn=skip_learn,
            cleanup_confirmed=result.cleanup_confirmed,
            down_flag=down_flag,
        )
    else:
        # Direct execution mode: merge + cleanup inline (no navigation, no source command)
        _execute_land_directly(
            ctx,
            repo=repo,
            target=land_target,
            script=script,
            pull_flag=pull_flag,
            no_delete=no_delete,
            skip_learn=skip_learn,
            cleanup_confirmed=result.cleanup_confirmed,
        )
