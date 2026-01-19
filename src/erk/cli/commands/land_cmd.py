"""Unified land command for PRs.

This command merges a PR and cleans up the worktree/branch.
It accepts a branch name, PR number, or PR URL as argument.

Usage:
    erk land              # Land current branch's PR
    erk land 123          # Land PR by number
    erk land <url>        # Land PR by URL
    erk land <branch>     # Land PR for branch
"""

import re
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Literal, NamedTuple

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
from erk.cli.commands.slot.common import (
    extract_slot_number,
    find_branch_assignment,
    get_placeholder_branch_name,
)
from erk.cli.commands.slot.unassign_cmd import execute_unassign
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext, create_context
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    SlotAssignment,
    load_pool_state,
    save_pool_state,
    update_slot_objective,
)
from erk_shared.gateway.console.real import InteractiveConsole
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.types import LandPrError
from erk_shared.github.types import PRDetails, PRNotFound
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import machine_output, user_output
from erk_shared.sessions.discovery import find_sessions_for_plan


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
    option to cancel and run learn manually first.

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
    try:
        issue = ctx.issues.get_issue(repo_root, plan_issue_number)
        if "erk-learn" in issue.labels:
            return
    except RuntimeError:
        # If we can't fetch the issue, continue with normal flow
        # (the sessions check will handle it)
        pass

    sessions = find_sessions_for_plan(ctx.issues, repo_root, plan_issue_number)

    if sessions.learn_session_ids:
        user_output(
            click.style("✓", fg="green") + f" Learn completed for plan #{plan_issue_number}"
        )
        return

    user_output(
        click.style("Warning: ", fg="yellow")
        + f"Plan #{plan_issue_number} has not been learned from."
    )
    user_output(
        f"\nTo extract insights from this plan's sessions, run:\n  erk learn {plan_issue_number}\n"
    )

    if not ctx.console.confirm("Continue landing without learning?", default=False):
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
    worktree_path = ctx.git.find_worktree_for_branch(repo_root, branch)
    if worktree_path is None:
        return None

    trunk_branch = ctx.git.detect_trunk_branch(repo_root)
    ctx.git.checkout_detached(worktree_path, trunk_branch)
    return worktree_path


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
    trunk = ctx.git.detect_trunk_branch(repo_root)
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
    merge_result = ctx.github.merge_pr(repo_root, pr_number, subject=subject, body=body)

    error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
    Ensure.invariant(
        merge_result is True,
        f"Failed to merge PR #{pr_number}\n\n{error_detail}",
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
        force: Whether to skip cleanup confirmation
        is_current_branch: True if landing from the branch's worktree
        target_child_branch: Target child branch for --up navigation (None for trunk)
        objective_number: Issue number of the objective linked to this branch (if any)
        no_delete: Whether to preserve the branch and slot assignment
        skip_activation_output: If True, skip activation message (used in execute mode
            where the script's cd command handles navigation)
    """
    # Handle --no-delete: skip cleanup, optionally navigate
    if no_delete:
        user_output(
            click.style("✓", fg="green")
            + f" Branch '{branch}' and slot assignment preserved (--no-delete)"
        )
        if is_current_branch:
            _navigate_after_land(
                ctx,
                repo=repo,
                script=script,
                pull_flag=pull_flag,
                target_child_branch=target_child_branch,
                skip_activation_output=skip_activation_output,
            )
        else:
            raise SystemExit(0)
        return

    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    if worktree_path is not None:
        # Check if this is a slot worktree by branch name
        # Using branch name is more reliable than path comparison which can fail
        # with symlinks, different erk_root values, or path representation inconsistencies
        state = load_pool_state(repo.pool_json_path)
        assignment: SlotAssignment | None = None
        if state is not None:
            assignment = find_branch_assignment(state, branch)

        if assignment is not None:
            # Slot worktree: unassign instead of delete
            # state is guaranteed to be non-None since assignment was found in it
            assert state is not None
            if not force and not ctx.dry_run:
                if not ctx.console.confirm(
                    f"Unassign slot '{assignment.slot_name}' and delete branch '{branch}'?",
                    default=True,
                ):
                    user_output("Slot preserved. Branch still exists locally.")
                    return
            # Record objective on slot BEFORE unassigning (so it persists after assignment removed)
            if objective_number is not None:
                state = update_slot_objective(state, assignment.slot_name, objective_number)
                if ctx.dry_run:
                    user_output("[DRY RUN] Would save pool state")
                else:
                    save_pool_state(repo.pool_json_path, state)
            execute_unassign(ctx, repo, state, assignment)
            # Defensive: ensure branch is released before deletion
            # (handles stale pool state where worktree_path doesn't match actual location)
            _ensure_branch_not_checked_out(ctx, repo_root=main_repo_root, branch=branch)
            ctx.branch_manager.delete_branch(main_repo_root, branch)
            user_output(click.style("✓", fg="green") + " Unassigned slot and deleted branch")
        elif extract_slot_number(worktree_path.name) is not None:
            # Slot worktree without assignment (e.g., branch checked out via gt get)
            # Don't delete the worktree - just delete branch and checkout placeholder
            slot_name = worktree_path.name

            if not force and not ctx.dry_run:
                user_output(
                    click.style("Warning:", fg="yellow")
                    + f" Slot '{slot_name}' has no assignment (branch checked out outside erk)."
                )
                user_output("  Use `erk pr co` or `erk branch checkout` to track slot usage.")
                if not ctx.console.confirm(
                    f"Release slot '{slot_name}' and delete branch '{branch}'?",
                    default=True,
                ):
                    user_output("Slot preserved. Branch still exists locally.")
                    return

            # Checkout placeholder branch before deleting the feature branch
            placeholder = get_placeholder_branch_name(slot_name)
            if placeholder is not None:
                ctx.git.checkout_branch(worktree_path, placeholder)

            # Defensive: ensure branch is released before deletion
            _ensure_branch_not_checked_out(ctx, repo_root=main_repo_root, branch=branch)
            ctx.branch_manager.delete_branch(main_repo_root, branch)
            user_output(click.style("✓", fg="green") + " Released slot and deleted branch")
        else:
            # Non-slot worktree: preserve worktree, delete branch only
            # Check for uncommitted changes before switching branches
            Ensure.invariant(
                not ctx.git.has_uncommitted_changes(worktree_path),
                f"Worktree has uncommitted changes at {worktree_path}.\n"
                "Commit or stash your changes before landing.",
            )

            if not force and not ctx.dry_run:
                if not ctx.console.confirm(
                    f"Delete branch '{branch}'? (worktree preserved)",
                    default=True,
                ):
                    user_output("Branch preserved.")
                    return

            # Checkout detached HEAD at trunk before deleting feature branch
            # (git won't delete a branch that's checked out in any worktree)
            # Use detached HEAD instead of checkout_branch because trunk may already
            # be checked out in the root worktree
            trunk_branch = ctx.git.detect_trunk_branch(main_repo_root)
            ctx.git.checkout_detached(worktree_path, trunk_branch)

            # Defensive: verify checkout succeeded before deletion
            _ensure_branch_not_checked_out(ctx, repo_root=main_repo_root, branch=branch)
            ctx.branch_manager.delete_branch(main_repo_root, branch)
            user_output(
                click.style("✓", fg="green")
                + f" Deleted branch (worktree '{worktree_path.name}' detached at '{trunk_branch}')"
            )
    else:
        # No worktree - check if branch exists locally before deletion (LBYL)
        local_branches = ctx.git.list_local_branches(main_repo_root)
        if branch in local_branches:
            ctx.branch_manager.delete_branch(main_repo_root, branch)
            user_output(click.style("✓", fg="green") + f" Deleted branch '{branch}'")
        # else: Branch doesn't exist locally - no cleanup needed (remote implementation or fork PR)

    # In dry-run mode, skip navigation and show summary
    if ctx.dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Navigate (only if we were in the deleted worktree)
    if is_current_branch:
        _navigate_after_land(
            ctx,
            repo=repo,
            script=script,
            pull_flag=pull_flag,
            target_child_branch=target_child_branch,
            skip_activation_output=skip_activation_output,
        )
    else:
        if script:
            # Output no-op script for shell integration consistency
            script_content = render_activation_script(
                worktree_path=ctx.cwd,
                target_subpath=None,
                post_cd_commands=None,
                final_message='echo "Land complete"',
                comment="land complete (no navigation needed)",
            )
            result = ctx.script_writer.write_activation_script(
                script_content,
                command_name="land",
                comment="no-op",
            )
            machine_output(str(result.path), nl=False)
        raise SystemExit(0)


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
        target_path = ctx.git.find_worktree_for_branch(main_repo_root, target_child_branch)
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
            trunk_branch = ctx.git.detect_trunk_branch(main_repo_root)
            user_output(f"Pulling latest changes from origin/{trunk_branch}...")
            try:
                ctx.git.pull_branch(main_repo_root, "origin", trunk_branch, ff_only=True)
            except subprocess.CalledProcessError:
                user_output(
                    click.style("Warning: ", fg="yellow") + "git pull failed (try running manually)"
                )

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
    target_child_branch: str | None,
    objective_number: int | None,
    use_graphite: bool,
    pull_flag: bool,
    no_delete: bool,
    target_path: Path,
) -> str:
    """Generate shell script that executes land and navigates.

    This script is generated after validation passes. When sourced, it:
    1. Calls `erk land --execute` with pre-validated state
    2. Navigates to the target location (trunk or child branch)

    Note: The execute phase always skips confirmation prompts because the user
    already approved by sourcing the script. --force is not passed because
    _execute_land handles this internally.

    Args:
        pr_number: PR number to merge
        branch: Branch name being landed
        worktree_path: Path to worktree being cleaned up (if any)
        is_current_branch: Whether landing from the branch's own worktree
        target_child_branch: Target child branch for --up navigation
        objective_number: Linked objective issue number (if any)
        use_graphite: Whether to use Graphite for merge
        pull_flag: Whether to pull after landing
        no_delete: Whether to preserve branch and slot
        target_path: Where to cd after land completes

    Returns:
        Shell script content as string
    """
    # Build erk land --execute command with all state parameters
    cmd_parts = ["erk land --execute"]
    cmd_parts.append(f"--exec-pr-number={pr_number}")
    cmd_parts.append(f"--exec-branch={branch}")
    if worktree_path is not None:
        cmd_parts.append(f"--exec-worktree-path={worktree_path}")
    if is_current_branch:
        cmd_parts.append("--exec-is-current-branch")
    if target_child_branch is not None:
        cmd_parts.append(f"--exec-target-child={target_child_branch}")
    if objective_number is not None:
        cmd_parts.append(f"--exec-objective-number={objective_number}")
    if use_graphite:
        cmd_parts.append("--exec-use-graphite")
    if not pull_flag:
        cmd_parts.append("--no-pull")
    if no_delete:
        cmd_parts.append("--no-delete")

    erk_cmd = " ".join(cmd_parts)
    target_path_str = str(target_path)

    return f"""# erk land deferred execution
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
        pr_details = Ensure.unwrap_pr(
            ctx.github.get_pr(main_repo_root, pr_number),
            f"Pull request #{pr_number} not found.",
        )

        user_output(f"Merging PR #{pr_number}...")
        subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
        body = pr_details.body or None
        merge_result = ctx.github.merge_pr(main_repo_root, pr_number, subject=subject, body=body)

        error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
        Ensure.invariant(
            merge_result is True,
            f"Failed to merge PR #{pr_number}\n\n{error_detail}",
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

    # Step 3: Cleanup (delete branch, unassign slot)
    # Note: Navigation is handled by the activation script's cd command
    # Always use force=True in execute mode because user already approved by
    # sourcing the script. Confirmations happen during validation phase only.
    _cleanup_and_navigate(
        ctx,
        repo=repo,
        branch=branch,
        worktree_path=worktree_path,
        script=script,
        pull_flag=pull_flag,
        force=True,  # Execute mode skips confirmations (user approved via script)
        is_current_branch=is_current_branch,
        target_child_branch=target_child_branch,
        objective_number=objective_number,
        no_delete=no_delete,
        skip_activation_output=True,  # Script's cd command handles navigation
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
# Hidden options for deferred execution (used by activation script)
@click.option("--execute", is_flag=True, hidden=True)
@click.option("--exec-pr-number", type=int, hidden=True)
@click.option("--exec-branch", hidden=True)
@click.option("--exec-worktree-path", type=click.Path(), hidden=True)
@click.option("--exec-is-current-branch", is_flag=True, hidden=True)
@click.option("--exec-target-child", hidden=True)
@click.option("--exec-objective-number", type=int, hidden=True)
@click.option("--exec-use-graphite", is_flag=True, hidden=True)
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
    execute: bool,
    exec_pr_number: int | None,
    exec_branch: str | None,
    exec_worktree_path: str | None,
    exec_is_current_branch: bool,
    exec_target_child: str | None,
    exec_objective_number: int | None,
    exec_use_graphite: bool,
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
    # Execute mode: skip validation and perform deferred operations from activation script
    if execute:
        _execute_land(
            ctx,
            pr_number=exec_pr_number,
            branch=exec_branch,
            worktree_path=Path(exec_worktree_path) if exec_worktree_path else None,
            is_current_branch=exec_is_current_branch,
            target_child_branch=exec_target_child,
            objective_number=exec_objective_number,
            use_graphite=exec_use_graphite,
            pull_flag=pull_flag,
            no_delete=no_delete,
            script=script,
        )
        return

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

    # Determine if landing current branch or a specific target
    if target is None:
        # Landing current branch's PR (original behavior)
        _land_current_branch(
            ctx,
            repo=repo,
            script=script,
            up_flag=up_flag,
            force=force,
            pull_flag=pull_flag,
            no_delete=no_delete,
        )
    else:
        # Parse the target argument
        parsed = parse_argument(target)

        if parsed.arg_type == "branch":
            # Landing a PR for a specific branch
            _land_by_branch(
                ctx,
                repo=repo,
                script=script,
                force=force,
                pull_flag=pull_flag,
                branch_name=target,
                no_delete=no_delete,
            )
        else:
            # Landing a specific PR by number or URL
            pr_number = Ensure.not_none(
                parsed.pr_number,
                f"Invalid PR identifier: {target}\nExpected a PR number (e.g., 123) or GitHub URL.",
            )
            _land_specific_pr(
                ctx,
                repo=repo,
                script=script,
                up_flag=up_flag,
                force=force,
                pull_flag=pull_flag,
                pr_number=pr_number,
                no_delete=no_delete,
            )


def _land_current_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
    no_delete: bool,
) -> None:
    """Land the current branch's PR (original behavior)."""
    check_clean_working_tree(ctx)

    # Get current branch and worktree path before landing
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    current_worktree_path = Ensure.not_none(
        ctx.git.find_worktree_for_branch(repo.root, current_branch),
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
    if ctx.branch_manager.is_graphite_managed():
        parent = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
        trunk = ctx.git.detect_trunk_branch(repo.root)
        Ensure.invariant(
            parent == trunk,
            f"Branch must be exactly one level up from {trunk}\n"
            f"Current branch: {current_branch}\n"
            f"Parent branch: {parent or 'unknown'} (expected: {trunk})\n\n"
            f"Please navigate to a branch that branches directly from {trunk}.",
        )

    # Look up PR for current branch to check unresolved comments BEFORE merge
    pr_details = ctx.github.get_pr_for_branch(repo.root, current_branch)
    if not isinstance(pr_details, PRNotFound):
        check_unresolved_comments(ctx, repo.root, pr_details.number, force=force)

    # Check learn status before any mutations (for plan branches)
    plan_issue_number = extract_leading_issue_number(current_branch)
    if plan_issue_number is not None:
        main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
        _check_learn_status_and_prompt(
            ctx,
            repo_root=main_repo_root,
            plan_issue_number=plan_issue_number,
            force=force,
            script=script,
        )

    # Validate PR exists and is landable
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    unwrapped_pr = Ensure.unwrap_pr(
        pr_details, f"No pull request found for branch '{current_branch}'."
    )
    pr_number = unwrapped_pr.number

    # Validate PR is open (not already merged or closed)
    Ensure.invariant(
        unwrapped_pr.state == "OPEN",
        f"Pull request is not open (state: {unwrapped_pr.state}).\n"
        f"PR #{pr_number} has already been {unwrapped_pr.state.lower()}.",
    )

    # Check for linked objective (needed for script generation)
    objective_number = get_objective_for_branch(ctx, main_repo_root, current_branch)

    # Check for slot assignment (needed for dry-run output)
    # Note: Confirmation for slot unassign happens in execute phase (_cleanup_and_navigate)
    state = load_pool_state(repo.pool_json_path)
    slot_assignment: SlotAssignment | None = None
    if state is not None:
        slot_assignment = find_branch_assignment(state, current_branch)

    # Determine target path for navigation after landing
    if target_child_branch is not None:
        # --up mode: navigate to child branch worktree
        target_path = ctx.git.find_worktree_for_branch(main_repo_root, target_child_branch)
        if target_path is None:
            # Will auto-create worktree in execute phase
            if repo.worktrees_dir:
                target_path = repo.worktrees_dir / target_child_branch
            else:
                target_path = main_repo_root
    else:
        # Navigate to trunk/root
        target_path = main_repo_root

    # Handle dry-run mode: show what would happen without generating script
    if ctx.dry_run:
        user_output(f"Would merge PR #{pr_number} for branch '{current_branch}'")
        if slot_assignment is not None:
            user_output(f"Would unassign slot '{slot_assignment.slot_name}'")
        user_output(f"Would delete branch '{current_branch}'")
        user_output(f"Would navigate to {target_path}")
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Generate execution script with all pre-validated state
    script_content = render_land_execution_script(
        pr_number=pr_number,
        branch=current_branch,
        worktree_path=current_worktree_path,
        is_current_branch=True,
        target_child_branch=target_child_branch,
        objective_number=objective_number,
        use_graphite=ctx.branch_manager.is_graphite_managed(),
        pull_flag=pull_flag,
        no_delete=no_delete,
        target_path=target_path,
    )

    # Write script to .erk/bin/land.sh
    result = ctx.script_writer.write_worktree_script(
        script_content,
        worktree_path=current_worktree_path,
        script_name="land",
        command_name="land",
        comment=f"land {current_branch}",
    )

    if script:
        # Shell integration mode: output just the path
        machine_output(str(result.path), nl=False)
    else:
        # Interactive mode: show instructions and copy to clipboard
        print_temp_script_instructions(
            result.path,
            instruction="To land the PR:",
            copy=True,
        )
    raise SystemExit(0)


def _land_specific_pr(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
    pr_number: int,
    no_delete: bool,
) -> None:
    """Land a specific PR by number."""
    # Validate --up is not used with PR argument
    Ensure.invariant(
        not up_flag,
        "Cannot use --up when specifying a PR.\n"
        "The --up flag only works when landing the current branch's PR.",
    )

    # Fetch PR details
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    pr_details = Ensure.unwrap_pr(
        ctx.github.get_pr(main_repo_root, pr_number),
        f"Pull request #{pr_number} not found.",
    )

    # Resolve branch name (handles fork PRs)
    branch = resolve_branch_for_pr(ctx, main_repo_root, pr_details)

    # Determine if we're in the target branch's worktree
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    is_current_branch = current_branch == branch

    # Check if we're in a worktree for this branch
    worktree_path = ctx.git.find_worktree_for_branch(main_repo_root, branch)

    # If in target worktree, validate clean working tree
    if is_current_branch:
        check_clean_working_tree(ctx)

    # Validate PR state
    Ensure.invariant(
        pr_details.state == "OPEN",
        f"Pull request #{pr_number} is not open (state: {pr_details.state}).",
    )

    # Validate PR base is trunk
    trunk = ctx.git.detect_trunk_branch(main_repo_root)
    Ensure.invariant(
        pr_details.base_ref_name == trunk,
        f"PR #{pr_number} targets '{pr_details.base_ref_name}' "
        + f"but should target '{trunk}'.\n\n"
        + "The GitHub PR's base branch has diverged from your local stack.\n"
        + "Run: gt restack && gt submit\n"
        + f"Then retry: erk land {pr_number}",
    )

    # Check for unresolved comments BEFORE merge
    check_unresolved_comments(ctx, main_repo_root, pr_number, force=force)

    # Check learn status before any mutations (for plan branches with local worktrees)
    # Skip for remote-only PRs since there are no local Claude sessions to learn from
    plan_issue_number = extract_leading_issue_number(branch)
    if plan_issue_number is not None and worktree_path is not None:
        _check_learn_status_and_prompt(
            ctx,
            repo_root=main_repo_root,
            plan_issue_number=plan_issue_number,
            force=force,
            script=script,
        )

    # Check for linked objective (needed for script generation)
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch)

    # Check for slot assignment (needed for dry-run output)
    # Note: Confirmation for slot unassign happens in execute phase (_cleanup_and_navigate)
    state = load_pool_state(repo.pool_json_path)
    slot_assignment: SlotAssignment | None = None
    if state is not None:
        slot_assignment = find_branch_assignment(state, branch)

    # Determine target path for navigation (no --up for specific PR, always trunk)
    target_path = main_repo_root

    # Handle dry-run mode
    if ctx.dry_run:
        user_output(f"Would merge PR #{pr_number} for branch '{branch}'")
        if slot_assignment is not None:
            user_output(f"Would unassign slot '{slot_assignment.slot_name}'")
        user_output(f"Would delete branch '{branch}'")
        user_output(f"Would navigate to {target_path}")
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Generate execution script with pre-validated state
    # Note: specific PR landing doesn't support Graphite path (no stack validation)
    script_content = render_land_execution_script(
        pr_number=pr_number,
        branch=branch,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        target_child_branch=None,
        objective_number=objective_number,
        use_graphite=False,  # Specific PR landing uses GitHub API directly
        pull_flag=pull_flag,
        no_delete=no_delete,
        target_path=target_path,
    )

    # Write script to .erk/bin/land.sh (use worktree if available, else repo root)
    script_dir = worktree_path if worktree_path is not None else main_repo_root
    result = ctx.script_writer.write_worktree_script(
        script_content,
        worktree_path=script_dir,
        script_name="land",
        command_name="land",
        comment=f"land PR #{pr_number}",
    )

    if script:
        # Shell integration mode: output just the path
        machine_output(str(result.path), nl=False)
    else:
        # Interactive mode: show instructions and copy to clipboard
        print_temp_script_instructions(
            result.path,
            instruction=f"To land PR #{pr_number}:",
            copy=True,
        )
    raise SystemExit(0)


def _land_by_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    force: bool,
    pull_flag: bool,
    branch_name: str,
    no_delete: bool,
) -> None:
    """Land a PR for a specific branch."""
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Look up PR for branch
    pr_details = Ensure.unwrap_pr(
        ctx.github.get_pr_for_branch(main_repo_root, branch_name),
        f"No pull request found for branch '{branch_name}'.",
    )

    pr_number = pr_details.number

    # Determine if we're in the target branch's worktree
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    is_current_branch = current_branch == branch_name

    # Check if worktree exists for this branch
    worktree_path = ctx.git.find_worktree_for_branch(main_repo_root, branch_name)

    # If in target worktree, validate clean working tree
    if is_current_branch:
        check_clean_working_tree(ctx)

    # Validate PR state
    Ensure.invariant(
        pr_details.state == "OPEN",
        f"Pull request #{pr_number} is not open (state: {pr_details.state}).",
    )

    # Validate PR base is trunk
    trunk = ctx.git.detect_trunk_branch(main_repo_root)
    Ensure.invariant(
        pr_details.base_ref_name == trunk,
        f"PR #{pr_number} targets '{pr_details.base_ref_name}' "
        + f"but should target '{trunk}'.\n\n"
        + "The GitHub PR's base branch has diverged from your local stack.\n"
        + "Run: gt restack && gt submit\n"
        + f"Then retry: erk land {branch_name}",
    )

    # Check for unresolved comments BEFORE merge
    check_unresolved_comments(ctx, main_repo_root, pr_number, force=force)

    # Check learn status before any mutations (for plan branches with local worktrees)
    # Skip for remote-only PRs since there are no local Claude sessions to learn from
    plan_issue_number = extract_leading_issue_number(branch_name)
    if plan_issue_number is not None and worktree_path is not None:
        _check_learn_status_and_prompt(
            ctx,
            repo_root=main_repo_root,
            plan_issue_number=plan_issue_number,
            force=force,
            script=script,
        )

    # Check for linked objective (needed for script generation)
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch_name)

    # Check for slot assignment (needed for dry-run output)
    # Note: Confirmation for slot unassign happens in execute phase (_cleanup_and_navigate)
    state = load_pool_state(repo.pool_json_path)
    slot_assignment: SlotAssignment | None = None
    if state is not None:
        slot_assignment = find_branch_assignment(state, branch_name)

    # Determine target path for navigation (no --up for branch landing, always trunk)
    target_path = main_repo_root

    # Handle dry-run mode
    if ctx.dry_run:
        user_output(f"Would merge PR #{pr_number} for branch '{branch_name}'")
        if slot_assignment is not None:
            user_output(f"Would unassign slot '{slot_assignment.slot_name}'")
        user_output(f"Would delete branch '{branch_name}'")
        user_output(f"Would navigate to {target_path}")
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    # Generate execution script with pre-validated state
    # Note: branch landing doesn't support Graphite path (no stack validation)
    script_content = render_land_execution_script(
        pr_number=pr_number,
        branch=branch_name,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        target_child_branch=None,
        objective_number=objective_number,
        use_graphite=False,  # Branch landing uses GitHub API directly
        pull_flag=pull_flag,
        no_delete=no_delete,
        target_path=target_path,
    )

    # Write script to .erk/bin/land.sh (use worktree if available, else repo root)
    script_dir = worktree_path if worktree_path is not None else main_repo_root
    result = ctx.script_writer.write_worktree_script(
        script_content,
        worktree_path=script_dir,
        script_name="land",
        command_name="land",
        comment=f"land {branch_name}",
    )

    if script:
        # Shell integration mode: output just the path
        machine_output(str(result.path), nl=False)
    else:
        # Interactive mode: show instructions and copy to clipboard
        print_temp_script_instructions(
            result.path,
            instruction=f"To land branch '{branch_name}':",
            copy=True,
        )
    raise SystemExit(0)
