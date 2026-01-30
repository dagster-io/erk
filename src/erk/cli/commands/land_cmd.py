"""Unified land command for PRs.

This command merges a PR and cleans up the worktree/branch.
It accepts a branch name, PR number, or PR URL as argument.

Usage:
    erk land              # Land current branch's PR
    erk land 123          # Land PR by number
    erk land <url>        # Land PR by URL
    erk land <branch>     # Land PR for branch
"""

import json
import re
import subprocess
from dataclasses import dataclass, replace
from enum import Enum, auto
from pathlib import Path
from typing import Literal, NamedTuple, assert_never

import click

from erk.cli.activation import print_temp_script_instructions, render_activation_script
from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
)
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    prompt_objective_update,
)
from erk.cli.commands.review_pr_cleanup import cleanup_review_pr
from erk.cli.commands.slot.common import (
    extract_slot_number,
    find_branch_assignment,
    get_placeholder_branch_name,
)
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.cli.commands.tripwire_promotion_helpers import (
    extract_tripwire_candidates_from_learn_plan,
    prompt_tripwire_promotion,
)
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
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
from erk_shared.gateway.console.real import InteractiveConsole
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_learn_status,
    extract_plan_header_learned_from_issue,
    update_plan_header_learn_plan_completed,
)
from erk_shared.gateway.github.types import BodyText, MergeError, PRDetails
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.types import LandPrError
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import machine_output, user_output
from erk_shared.sessions.discovery import find_sessions_for_plan
from erk_shared.stack.validation import validate_parent_is_trunk


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
    objective_number: int | None
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

    resolved = determine_cleanup_type(
        no_delete=False,  # no_delete handled separately in _handle_no_delete
        worktree_path=target.worktree_path,
        pool_json_path=repo.pool_json_path,
        branch=target.branch,
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
            user_output("  Use `erk pr co` or `erk branch checkout` to track slot usage.")
            proceed = ctx.console.confirm(
                f"After landing, release slot '{target.worktree_path.name}' "
                f"and delete branch '{target.branch}'?",
                default=True,
            )
        case CleanupType.NON_SLOT:
            proceed = ctx.console.confirm(
                f"After landing, delete branch '{target.branch}'? (worktree preserved)",
                default=True,
            )
        case _:
            assert_never(resolved.cleanup_type)

    return CleanupConfirmation(proceed=proceed)


def _check_learn_status_and_prompt(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_issue_number: int,
    force: bool,
    script: bool,
) -> None:
    """Check if plan has been learned from and prompt user if not.

    This provides a conservative check before landing - if the plan has associated
    sessions but hasn't been learned from yet, warn the user and give them the
    option to cancel, trigger async learn, or continue without learning.

    Learn plans (issues with erk-learn label) are skipped since they are for
    extracting insights, not for being "learned from" themselves.

    Args:
        ctx: ErkContext
        repo_root: Repository root path
        plan_issue_number: Issue number of the plan
        force: If True, skip the check entirely
        script: If True, output no-op activation script on abort

    Raises:
        SystemExit(0) if user declines to continue
    """
    if force:
        return

    # Check override chain: local_config overrides global_config
    # local_config contains merged repo+local values (local wins over repo)
    if ctx.local_config.prompt_learn_on_land is not None:
        # Repo or local level override exists
        if not ctx.local_config.prompt_learn_on_land:
            return
    elif ctx.global_config is not None and not ctx.global_config.prompt_learn_on_land:
        # Fall back to global config
        return

    # Skip learn check for learn plans (they don't need to be learned from)
    # Fetch issue to check labels and learn_status
    issue = ctx.issues.get_issue(repo_root, plan_issue_number)
    if "erk-learn" in issue.labels:
        return

    # Check learn_status from plan header metadata
    learn_status = extract_plan_header_learn_status(issue.body)

    # Handle completed statuses - learn has already finished
    completed_statuses = {"completed_no_plan", "completed_with_plan", "plan_completed"}
    if learn_status in completed_statuses:
        user_output(
            click.style("✓", fg="green") + f" Learn completed for plan #{plan_issue_number}"
        )
        return

    # Handle pending status - async learn is in progress
    if learn_status == "pending":
        user_output(
            click.style("⏳", fg="cyan") + f" Async learn in progress for plan #{plan_issue_number}"
        )
        return

    # learn_status is null or not_started - fall through to check sessions

    # Check for existing learn sessions (backward compatibility)
    sessions = find_sessions_for_plan(ctx.issues, repo_root, plan_issue_number)

    if sessions.learn_session_ids:
        user_output(
            click.style("✓", fg="green") + f" Learn completed for plan #{plan_issue_number}"
        )
        return

    # No learn has happened - prompt user for action
    _prompt_async_learn_and_continue(
        ctx,
        repo_root=repo_root,
        plan_issue_number=plan_issue_number,
        script=script,
    )


def _prompt_async_learn_and_continue(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_issue_number: int,
    script: bool,
) -> None:
    """Prompt user for async learn options when no learning has occurred.

    Offers three choices:
    1. Trigger async learn and continue - dispatches workflow, then lands
    2. Continue without learning - proceeds with landing
    3. Cancel - aborts landing

    Args:
        ctx: ErkContext
        repo_root: Repository root path
        plan_issue_number: Issue number of the plan
        script: If True, output no-op activation script on abort

    Raises:
        SystemExit(0) if user cancels
    """
    user_output(
        click.style("Warning: ", fg="yellow")
        + f"Plan #{plan_issue_number} has not been learned from."
    )
    user_output("")

    # In script mode, auto-select "trigger async learn" as the default action
    if not ctx.console.is_stdin_interactive():
        _trigger_async_learn(ctx, repo_root=repo_root, plan_issue_number=plan_issue_number)
        return

    # Interactive mode: show numbered choice menu
    user_output("Choose an action:")
    user_output("  1. Trigger async learn and continue (recommended)")
    user_output("  2. Continue without learning")
    user_output("  3. Cancel")
    user_output("")

    choice = click.prompt(
        "Enter choice",
        type=click.IntRange(1, 3),
        default=1,
    )

    if choice == 1:
        # Trigger async learn workflow
        _trigger_async_learn(ctx, repo_root=repo_root, plan_issue_number=plan_issue_number)
    elif choice == 2:
        # Continue without learning
        user_output("Continuing without learning.")
    else:
        # Cancel
        user_output("Cancelled. Run 'erk learn' first, then retry landing.")
        if script:
            script_content = render_activation_script(
                worktree_path=ctx.cwd,
                target_subpath=None,
                post_cd_commands=None,
                final_message='echo "Cancelled - run erk learn first"',
                comment="land cancelled (learn check)",
            )
            result = ctx.script_writer.write_activation_script(
                script_content,
                command_name="land",
                comment="cancelled",
            )
            machine_output(str(result.path), nl=False)
        raise SystemExit(0)


def _trigger_async_learn(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_issue_number: int,
) -> None:
    """Trigger async learn workflow for a plan issue.

    Calls `erk exec trigger-async-learn` via subprocess and reports result.
    This is a fire-and-forget operation - landing continues immediately.

    Args:
        ctx: ErkContext
        repo_root: Repository root path (unused, for consistency)
        plan_issue_number: Issue number of the plan
    """
    # Silence unused parameter warning - repo_root kept for interface consistency
    _ = repo_root

    user_output(f"Triggering async learn for plan #{plan_issue_number}...")

    try:
        # Stream stderr (progress) in real-time while capturing stdout (JSON result)
        process = subprocess.Popen(
            ["erk", "exec", "trigger-async-learn", str(plan_issue_number)],
            stdout=subprocess.PIPE,
            stderr=None,  # Inherit stderr - progress streams through
            text=True,
            cwd=ctx.cwd,
        )
        stdout, _ = process.communicate()
    except FileNotFoundError:
        msg = "Could not trigger async learn: erk command not found"
        user_output(click.style("⚠ ", fg="yellow") + msg)
        return

    if process.returncode != 0:
        error_msg = _parse_trigger_error(stdout, "")
        msg = f"Could not trigger async learn: {error_msg}"
        user_output(click.style("⚠ ", fg="yellow") + msg)
        return

    # Parse output JSON to get workflow_url
    output = json.loads(stdout)
    if output.get("success"):
        workflow_url = output.get("workflow_url", "")
        if workflow_url:
            user_output(click.style("✓", fg="green") + f" Async learn triggered: {workflow_url}")
        else:
            # Fallback for backwards compatibility
            user_output(
                click.style("✓", fg="green")
                + f" Async learn triggered (run: {output.get('run_id', 'unknown')})"
            )
    else:
        user_output(
            click.style("⚠ ", fg="yellow")
            + f"Async learn response: {output.get('error', 'unknown error')}"
        )


def _parse_trigger_error(stdout: str, stderr: str) -> str:
    """Parse error message from trigger-async-learn failure.

    Attempts to extract error from JSON stdout, falls back to stderr or stdout.
    """
    # Check if stdout looks like JSON (starts with {) before parsing
    if stdout and stdout.strip().startswith("{"):
        try:
            error_output = json.loads(stdout)
            error = error_output.get("error")
            if error:
                return error
        except json.JSONDecodeError:
            pass  # Fall through to return raw stderr/stdout
    return stderr or stdout or "unknown error"


def _update_parent_learn_status_if_learn_plan(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_issue_number: int,
    pr_number: int,
) -> None:
    """Update parent plan's learn_status to plan_completed if this is a learn plan.

    Learn plans have a 'learned_from_issue' field in their plan-header that points
    to the parent plan they were generated from. When a learn plan is landed, we
    update the parent plan to record:
    - learn_status: "plan_completed"
    - learn_plan_pr: the PR number that implemented the learn plan

    Args:
        ctx: ErkContext
        repo_root: Repository root path
        plan_issue_number: Issue number of the plan being landed
        pr_number: PR number that merged this plan
    """
    # Check if plan issue exists before fetching
    if not ctx.issues.issue_exists(repo_root, plan_issue_number):
        return

    issue = ctx.issues.get_issue(repo_root, plan_issue_number)
    learned_from = extract_plan_header_learned_from_issue(issue.body)

    if learned_from is None:
        # Not a learn plan - nothing to update
        return

    # Check if parent issue exists before fetching
    if not ctx.issues.issue_exists(repo_root, learned_from):
        return

    parent_issue = ctx.issues.get_issue(repo_root, learned_from)
    updated_body = update_plan_header_learn_plan_completed(
        issue_body=parent_issue.body,
        learn_plan_pr=pr_number,
    )
    ctx.issues.update_issue_body(repo_root, learned_from, BodyText(content=updated_body))
    user_output(f"Updated learn status on parent plan #{learned_from}")


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
        cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch)
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
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch)
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
        cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, placeholder)

    # Defensive: ensure branch is released before deletion
    _ensure_branch_not_checked_out(
        cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
    )
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch)
    user_output(click.style("✓", fg="green") + " Released slot and deleted branch")


def _cleanup_non_slot_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup for non-slot worktree: checkout detached HEAD, delete branch."""
    # worktree_path is guaranteed non-None since we're in a non-slot worktree
    assert cleanup.worktree_path is not None

    # Check for uncommitted changes before switching branches
    Ensure.invariant(
        not cleanup.ctx.git.status.has_uncommitted_changes(cleanup.worktree_path),
        f"Worktree has uncommitted changes at {cleanup.worktree_path}.\n"
        "Commit or stash your changes before landing.",
    )

    if not cleanup.cleanup_confirmed:
        user_output("Branch preserved.")
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
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch)

    # Try to checkout trunk branch after deletion to exit detached HEAD state.
    # Only possible if trunk is not already checked out in another worktree.
    trunk_worktree = cleanup.ctx.git.worktree.find_worktree_for_branch(
        cleanup.main_repo_root, trunk_branch
    )
    if trunk_worktree is None:
        # Trunk is not checked out elsewhere - safe to checkout
        cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, trunk_branch)
        user_output(
            click.style("✓", fg="green")
            + f" Deleted branch (worktree '{cleanup.worktree_path.name}' on '{trunk_branch}')"
        )
    else:
        # Trunk is checked out in another worktree - must stay detached
        worktree_name = cleanup.worktree_path.name
        user_output(
            click.style("✓", fg="green")
            + f" Deleted branch (worktree '{worktree_name}' detached at '{trunk_branch}')"
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

    # 5. Learn status check (for plan branches)
    # Check when: has plan issue AND (is_current_branch OR has worktree)
    plan_issue_number = extract_leading_issue_number(target.branch)
    if plan_issue_number is not None and (
        target.is_current_branch or target.worktree_path is not None
    ):
        _check_learn_status_and_prompt(
            ctx,
            repo_root=main_repo_root,
            plan_issue_number=plan_issue_number,
            force=force,
            script=script,
        )

    # 6. Gather cleanup confirmation upfront (all confirms batched before mutations)
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


def _land_target(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    target: LandTarget,
    script: bool,
    force: bool,
    pull_flag: bool,
    no_delete: bool,
) -> None:
    """Unified landing flow for all entry points.

    This function handles the common landing workflow after target resolution:
    1. Validate PR is ready to land
    2. Look up objective and slot assignment
    3. Determine navigation target path
    4. Handle dry-run mode
    5. Generate and write execution script
    6. Display instructions or output script path

    Args:
        ctx: ErkContext
        repo: Repository context
        target: Resolved landing target
        script: Whether to output machine-readable script path
        force: Skip confirmation prompts
        pull_flag: Whether to pull after landing
        no_delete: Preserve branch after landing

    Raises:
        SystemExit(0) after outputting script instructions
        SystemExit(1) on validation failure
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    pr_number = target.pr_details.number
    branch = target.branch

    # Step 1: Validate PR is ready to land (gathers all confirmations upfront)
    # The returned confirmation captures whether user approved cleanup.
    # In script mode, execute phase uses cleanup_confirmed=True (user approved by sourcing).
    _cleanup_confirmation = _validate_pr_for_landing(
        ctx, repo=repo, target=target, force=force, script=script
    )
    # Note: _cleanup_confirmation is intentionally unused here because _land_target
    # outputs a script that runs in a separate process. The confirmation has already
    # been gathered (user was prompted), and the execute phase will use
    # cleanup_confirmed=True since the user approved by sourcing the script.
    _ = _cleanup_confirmation

    # Step 2: Look up objective for branch (needed for script generation)
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch)

    # Step 3: Look up slot assignment (needed for dry-run output)
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
        use_graphite=target.use_graphite,
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


def _execute_simple_land(
    ctx: ErkContext,
    *,
    repo_root: Path,
    branch: str,
    pr_details: PRDetails,
) -> int:
    """Execute simple GitHub-only merge without Graphite stack validation.

    This is the non-Graphite path for landing PRs. It performs:
    1. PR state validation (must be OPEN)
    2. Base branch validation (must target trunk)
    3. GitHub merge API call

    Args:
        ctx: ErkContext
        repo_root: Repository root directory
        branch: Branch name being landed
        pr_details: PR details from GitHub

    Returns:
        PR number that was merged

    Raises:
        SystemExit(1) on validation or merge failure
    """
    pr_number = pr_details.number

    # Validate PR state
    Ensure.invariant(
        pr_details.state == "OPEN",
        f"Pull request #{pr_number} is not open (state: {pr_details.state}).",
    )

    # Validate PR base is trunk
    trunk = ctx.git.branch.detect_trunk_branch(repo_root)
    Ensure.invariant(
        pr_details.base_ref_name == trunk,
        f"PR #{pr_number} targets '{pr_details.base_ref_name}' "
        + f"but should target '{trunk}'.\n\n"
        + "The GitHub PR's base branch has diverged from your local stack.\n"
        + "Update the PR base to trunk before landing.",
    )

    # Merge the PR via GitHub API
    user_output(f"Merging PR #{pr_number}...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body or None
    merge_result = ctx.github.merge_pr(
        repo_root,
        pr_number,
        squash=True,
        verbose=False,
        subject=subject,
        body=body,
    )

    if isinstance(merge_result, MergeError):
        Ensure.invariant(
            False,
            f"Failed to merge PR #{pr_number}\n\n{merge_result.message}",
        )

    return pr_number


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
    objective_number: int | None,
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
        objective_number: Issue number of the objective linked to this branch (if any)
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
        objective_number=objective_number,
        no_delete=no_delete,
        skip_activation_output=skip_activation_output,
        cleanup_confirmed=cleanup_confirmed,
    )

    resolved = determine_cleanup_type(
        no_delete=cleanup.no_delete,
        worktree_path=cleanup.worktree_path,
        pool_json_path=repo.pool_json_path,
        branch=branch,
    )

    match resolved.cleanup_type:
        case CleanupType.NO_DELETE:
            _handle_no_delete(cleanup)
            return
        case CleanupType.NO_WORKTREE:
            _cleanup_no_worktree(cleanup)
        case CleanupType.SLOT_ASSIGNED:
            assert resolved.pool_state is not None
            assert resolved.assignment is not None
            _cleanup_slot_with_assignment(
                cleanup, state=resolved.pool_state, assignment=resolved.assignment
            )
        case CleanupType.SLOT_UNASSIGNED:
            assert cleanup.worktree_path is not None
            _cleanup_slot_without_assignment(cleanup, slot_name=cleanup.worktree_path.name)
        case CleanupType.NON_SLOT:
            _cleanup_non_slot_worktree(cleanup)
        case _:
            assert_never(resolved.cleanup_type)

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
            # Auto-create worktree for child
            target_path, _ = ensure_worktree_for_branch(
                ctx, post_deletion_repo, target_child_branch
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
    use_graphite: bool,
    target_path: Path,
) -> str:
    """Generate shell script that executes land and navigates.

    This script is generated after validation passes. When sourced, it:
    1. Validates required arguments (PR number and branch)
    2. Calls `erk exec land-execute` with pre-validated state plus user flags
    3. Navigates to the target location (trunk or child branch)

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
    - --objective-number: linked objective
    - --use-graphite: whether Graphite is enabled

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
    if objective_number is not None:
        cmd_parts.append(f"--objective-number={objective_number}")
    if use_graphite:
        cmd_parts.append("--use-graphite")
    # User-controllable flags passed through "$@"
    cmd_parts.append('"$@"')

    erk_cmd = " ".join(cmd_parts)
    target_path_str = str(target_path)

    return f"""# erk land deferred execution
# Usage: source land.sh <pr_number> <branch> [flags...]
PR_NUMBER="${{1:?Error: PR number required}}"
BRANCH="${{2:?Error: Branch name required}}"
shift 2

{erk_cmd}
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
    objective_number: int | None,
    use_graphite: bool,
    pull_flag: bool,
    no_delete: bool,
    script: bool,
) -> None:
    """Execute deferred land operations from activation script.

    This function is called when `erk land --execute` is invoked by the
    activation script. All validation has already been done - this just
    performs the destructive operations.

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
        objective_number: Linked objective issue number (if any)
        use_graphite: Whether to use Graphite for merge
        pull_flag: Whether to pull after landing
        no_delete: Whether to preserve branch and slot
        script: Whether running in script mode
    """
    # Validate required parameters
    Ensure.invariant(pr_number is not None, "Missing --exec-pr-number in execute mode")
    Ensure.invariant(branch is not None, "Missing --exec-branch in execute mode")
    # Type narrowing for the type checker (invariants don't narrow types)
    assert pr_number is not None
    assert branch is not None

    repo = discover_repo_context(ctx, ctx.cwd)
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Step 1: Merge the PR
    # Use Graphite path only if:
    # 1. use_graphite is True, AND
    # 2. We have a worktree_path (i.e., there's a local checkout for this branch)
    #
    # For remote PRs (no local worktree), we use the simple GitHub merge path
    # because execute_land_pr requires being in the branch's worktree to get
    # the current branch and its parent.
    if use_graphite and worktree_path is not None:
        # Full Graphite-aware path - run from the branch's worktree
        result = render_events(execute_land_pr(ctx, worktree_path))

        if isinstance(result, LandPrError):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)

        merged_pr_number = result.pr_number
    else:
        # Simple GitHub-only merge (no worktree or Graphite disabled)
        pr_details = EnsureIdeal.unwrap_pr(
            ctx.github.get_pr(main_repo_root, pr_number),
            f"Pull request #{pr_number} not found.",
        )

        user_output(f"Merging PR #{pr_number}...")
        subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
        body = pr_details.body or None
        merge_result = ctx.github.merge_pr(
            main_repo_root,
            pr_number,
            squash=True,
            verbose=False,
            subject=subject,
            body=body,
        )

        if isinstance(merge_result, MergeError):
            Ensure.invariant(
                False,
                f"Failed to merge PR #{pr_number}\n\n{merge_result.message}",
            )
        merged_pr_number = pr_number

    user_output(click.style("✓", fg="green") + f" Merged PR #{merged_pr_number} [{branch}]")

    # Step 2: Handle objective update (non-interactive since user already approved)
    if objective_number is not None:
        prompt_objective_update(
            ctx,
            repo_root=main_repo_root,
            objective_number=objective_number,
            pr_number=merged_pr_number,
            branch=branch,
            force=True,  # Skip confirmation in execute mode
        )

    # Step 2.5: Update parent plan if this is a learn plan
    plan_issue_number = extract_leading_issue_number(branch)
    if plan_issue_number is not None:
        _update_parent_learn_status_if_learn_plan(
            ctx,
            repo_root=main_repo_root,
            plan_issue_number=plan_issue_number,
            pr_number=merged_pr_number,
        )

    # Step 2.75: Prompt tripwire promotion if this is a learn plan
    if plan_issue_number is not None:
        candidates = extract_tripwire_candidates_from_learn_plan(
            ctx,
            repo_root=main_repo_root,
            plan_issue_number=plan_issue_number,
        )
        if candidates:
            prompt_tripwire_promotion(
                ctx,
                repo_root=main_repo_root,
                candidates=candidates,
                force=True,  # Execute mode auto-promotes
            )

    # Step 2.8: Close review PR if plan has one
    if plan_issue_number is not None:
        cleanup_review_pr(
            ctx,
            repo_root=main_repo_root,
            issue_number=plan_issue_number,
            reason=f"the plan (issue #{plan_issue_number}) was implemented and landed",
        )

    # Step 3: Cleanup (delete branch, unassign slot)
    # Note: Navigation is handled by the activation script's cd command
    # Always use cleanup_confirmed=True in execute mode because user already approved
    # by sourcing the script. Confirmations happen during validation phase only.
    _cleanup_and_navigate(
        ctx,
        repo=repo,
        branch=branch,
        worktree_path=worktree_path,
        script=script,
        pull_flag=pull_flag,
        force=True,  # Legacy parameter, kept for compatibility
        is_current_branch=is_current_branch,
        target_child_branch=target_child_branch,
        objective_number=objective_number,
        no_delete=no_delete,
        skip_activation_output=True,  # Script's cd command handles navigation
        cleanup_confirmed=True,  # Execute mode: user approved via script
    )


@click.command("land", cls=CommandWithHiddenOptions)
@script_option
@click.argument("target", required=False)
@click.option(
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip all confirmation prompts (unresolved comments, worktree deletion)",
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
@click.pass_obj
def land(
    ctx: ErkContext,
    *,
    script: bool,
    target: str | None,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
    dry_run: bool,
    no_delete: bool,
) -> None:
    """Merge PR and delete worktree.

    Can land the current branch's PR, a specific PR by number/URL,
    or a PR for a specific branch.

    \b
    Usage:
      erk land              # Land current branch's PR
      erk land 123          # Land PR #123
      erk land <url>        # Land PR by GitHub URL
      erk land <branch>     # Land PR for branch

    Requires:
    - PR must be open and ready to merge
    - PR's base branch must be trunk

    Note: The --up flag requires Graphite for child branch tracking.
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

    # Validate prerequisites
    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Phase 1: Resolve landing target based on argument type
    if target is None:
        # Landing current branch's PR
        land_target = _resolve_land_target_current_branch(ctx, repo=repo, up_flag=up_flag)
    else:
        # Parse the target argument to determine type
        parsed = parse_argument(target)

        if parsed.arg_type == "branch":
            # Landing a PR for a specific branch
            land_target = _resolve_land_target_branch(ctx, repo=repo, branch_name=target)
        else:
            # Landing a specific PR by number or URL
            pr_number = Ensure.not_none(
                parsed.pr_number,
                f"Invalid PR identifier: {target}\nExpected a PR number (e.g., 123) or GitHub URL.",
            )
            land_target = _resolve_land_target_pr(
                ctx, repo=repo, pr_number=pr_number, up_flag=up_flag
            )

    # Phase 2: Execute unified landing flow
    _land_target(
        ctx,
        repo=repo,
        target=land_target,
        script=script,
        force=force,
        pull_flag=pull_flag,
        no_delete=no_delete,
    )
