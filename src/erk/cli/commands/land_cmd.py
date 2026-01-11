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

from erk.cli.commands.autolearn import maybe_create_autolearn_issue
from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
)
from erk.cli.commands.objective_helpers import (
    check_and_display_plan_issue_closure,
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
from erk_shared.gateway.graphite.disabled import GraphiteDisabled
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.types import LandPrError, LandPrSuccess
from erk_shared.github.types import PRDetails, PRNotFound
from erk_shared.output.output import user_output


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
        if not ctx.console.is_stdin_interactive():
            user_output(
                click.style("Error: ", fg="red")
                + "Cannot prompt for confirmation in non-interactive mode.\n"
                + "Use --force to skip this check."
            )
            raise SystemExit(1)
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
    if pr_details.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request #{pr_number} is not open (state: {pr_details.state})."
        )
        raise SystemExit(1)

    # Validate PR base is trunk
    trunk = ctx.git.detect_trunk_branch(repo_root)
    if pr_details.base_ref_name != trunk:
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{pr_number} targets '{pr_details.base_ref_name}' "
            + f"but should target '{trunk}'.\n\n"
            + "The GitHub PR's base branch has diverged from your local stack.\n"
            + "Update the PR base to trunk before landing."
        )
        raise SystemExit(1)

    # Merge the PR via GitHub API
    user_output(f"Merging PR #{pr_number}...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body or None
    merge_result = ctx.github.merge_pr(repo_root, pr_number, subject=subject, body=body)

    if merge_result is not True:
        error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
        user_output(
            click.style("Error: ", fg="red") + f"Failed to merge PR #{pr_number}\n\n{error_detail}"
        )
        raise SystemExit(1)

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
    autolearn: bool,
    pr_number: int,
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
        autolearn: Whether to create autolearn issue after confirmation
        pr_number: PR number that was merged (for autolearn)
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
            if ctx.git.has_uncommitted_changes(worktree_path):
                user_output(
                    click.style("Error: ", fg="red")
                    + f"Worktree has uncommitted changes at {worktree_path}.\n"
                    "Commit or stash your changes before landing."
                )
                raise SystemExit(1)

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

    # Create autolearn issue if enabled (after confirmation, before navigation)
    if autolearn:
        main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
        maybe_create_autolearn_issue(
            ctx, repo_root=main_repo_root, branch=branch, pr_number=pr_number
        )

    # Navigate (only if we were in the deleted worktree)
    if is_current_branch:
        _navigate_after_land(
            ctx,
            repo=repo,
            script=script,
            pull_flag=pull_flag,
            target_child_branch=target_child_branch,
        )
    else:
        # Command succeeded but no navigation needed - exit cleanly
        raise SystemExit(0)


def _navigate_after_land(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    pull_flag: bool,
    target_child_branch: str | None,
) -> None:
    """Navigate to appropriate location after landing.

    Args:
        ctx: ErkContext
        repo: Repository context
        script: Whether to output activation script
        pull_flag: Whether to include git pull in activation
        target_child_branch: If set, navigate to this child branch (--up mode)
    """
    # Create post-deletion repo context with root pointing to main_repo_root
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    post_deletion_repo = replace(repo, root=main_repo_root)

    if target_child_branch is not None:
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
        # Output activation script pointing to trunk/root repo
        activate_root_repo(
            ctx,
            repo=post_deletion_repo,
            script=script,
            command_name="land",
            post_cd_commands=None,
        )
        # activate_root_repo raises SystemExit(0)


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
    "--autolearn/--no-autolearn",
    "autolearn_flag",
    default=None,
    help="Override config to enable/disable automatic learn plan creation",
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
    autolearn_flag: bool | None,
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

    With shell integration (recommended):
      erk land

    Without shell integration:
      source <(erk land --script)

    Requires:
    - PR must be open and ready to merge
    - PR's base branch must be trunk

    Note: The --up flag requires Graphite for child branch tracking.
    """
    # Replace context with dry-run wrappers if needed
    if dry_run:
        ctx = create_context(dry_run=True)
        script = False  # Force human-readable output in dry-run mode

    # Compute effective autolearn: CLI flag overrides config
    if autolearn_flag is not None:
        autolearn = autolearn_flag
    elif ctx.global_config is not None:
        autolearn = ctx.global_config.autolearn
    else:
        autolearn = False

    # Validate prerequisites
    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Validate shell integration for activation script output (skip in dry-run mode)
    if not script and not ctx.dry_run:
        user_output(
            click.style("Error: ", fg="red")
            + "This command requires shell integration for activation.\n\n"
            + "Options:\n"
            + "  1. Use shell integration: erk land\n"
            + "     (Requires 'erk init --shell' setup)\n\n"
            + "  2. Use --script flag: source <(erk land --script)\n"
        )
        raise SystemExit(1)

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
            autolearn=autolearn,
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
                autolearn=autolearn,
                no_delete=no_delete,
            )
        else:
            # Landing a specific PR by number or URL
            if parsed.pr_number is None:
                user_output(
                    click.style("Error: ", fg="red") + f"Invalid PR identifier: {target}\n"
                    "Expected a PR number (e.g., 123) or GitHub URL."
                )
                raise SystemExit(1)
            _land_specific_pr(
                ctx,
                repo=repo,
                script=script,
                up_flag=up_flag,
                force=force,
                pull_flag=pull_flag,
                pr_number=parsed.pr_number,
                autolearn=autolearn,
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
    autolearn: bool,
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
        if isinstance(ctx.graphite, GraphiteDisabled):
            user_output(
                click.style("Error: ", fg="red")
                + "--up flag requires Graphite for child branch tracking.\n\n"
                + "To enable Graphite: erk config set use_graphite true\n\n"
                + "Without --up, erk land will navigate to trunk after landing."
            )
            raise SystemExit(1)

        children = ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch)
        if len(children) == 0:
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has no children.\n"
                "Use 'erk land' without --up to return to trunk."
            )
            raise SystemExit(1)
        elif len(children) > 1:
            children_list = ", ".join(f"'{c}'" for c in children)
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has multiple children: "
                f"{children_list}.\n"
                "Use 'erk land' without --up, then 'erk co <branch>' to choose."
            )
            raise SystemExit(1)
        else:
            target_child_branch = children[0]

    # Look up PR for current branch to check unresolved comments BEFORE merge
    pr_details = ctx.github.get_pr_for_branch(repo.root, current_branch)
    if not isinstance(pr_details, PRNotFound):
        check_unresolved_comments(ctx, repo.root, pr_details.number, force=force)

    # Step 1: Execute land (merges the PR)
    if isinstance(ctx.graphite, GraphiteDisabled):
        # Simple GitHub-only merge path (no stack validation)
        if isinstance(pr_details, PRNotFound):
            user_output(
                click.style("Error: ", fg="red")
                + f"No pull request found for branch '{current_branch}'."
            )
            raise SystemExit(1)
        merged_pr_number = _execute_simple_land(
            ctx, repo_root=repo.root, branch=current_branch, pr_details=pr_details
        )
        pr_body = pr_details.body or ""
    else:
        # Full Graphite-aware path with stack validation
        # render_events() uses click.echo() + sys.stderr.flush() for immediate unbuffered output
        result = render_events(execute_land_pr(ctx, ctx.cwd))

        if isinstance(result, LandPrError):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)

        # Success - PR was merged
        success_result: LandPrSuccess = result
        merged_pr_number = success_result.pr_number
        # For Graphite path, we need to fetch PR details to get body
        pr_body = pr_details.body if not isinstance(pr_details, PRNotFound) else ""

    user_output(click.style("✓", fg="green") + f" Merged PR #{merged_pr_number} [{current_branch}]")

    # Check and display plan issue closure
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    check_and_display_plan_issue_closure(ctx, main_repo_root, current_branch, pr_body=pr_body)

    # Check for linked objective and offer to update
    objective_number = get_objective_for_branch(ctx, main_repo_root, current_branch)
    if objective_number is not None:
        prompt_objective_update(
            ctx,
            repo_root=main_repo_root,
            objective_number=objective_number,
            pr_number=merged_pr_number,
            branch=current_branch,
            force=force,
        )

    # Step 2: Cleanup and navigate (autolearn happens inside after confirmation)
    _cleanup_and_navigate(
        ctx,
        repo=repo,
        branch=current_branch,
        worktree_path=current_worktree_path,
        script=script,
        pull_flag=pull_flag,
        force=force,
        is_current_branch=True,
        target_child_branch=target_child_branch,
        objective_number=objective_number,
        no_delete=no_delete,
        autolearn=autolearn,
        pr_number=merged_pr_number,
    )


def _land_specific_pr(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
    pr_number: int,
    autolearn: bool,
    no_delete: bool,
) -> None:
    """Land a specific PR by number."""
    # Validate --up is not used with PR argument
    if up_flag:
        user_output(
            click.style("Error: ", fg="red") + "Cannot use --up when specifying a PR.\n"
            "The --up flag only works when landing the current branch's PR."
        )
        raise SystemExit(1)

    # Fetch PR details
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    pr_details = ctx.github.get_pr(main_repo_root, pr_number)

    if isinstance(pr_details, PRNotFound):
        user_output(click.style("Error: ", fg="red") + f"Pull request #{pr_number} not found.")
        raise SystemExit(1)

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
    if pr_details.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request #{pr_number} is not open (state: {pr_details.state})."
        )
        raise SystemExit(1)

    # Validate PR base is trunk
    trunk = ctx.git.detect_trunk_branch(main_repo_root)
    if pr_details.base_ref_name != trunk:
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{pr_number} targets '{pr_details.base_ref_name}' "
            + f"but should target '{trunk}'.\n\n"
            + "The GitHub PR's base branch has diverged from your local stack.\n"
            + "Run: gt restack && gt submit\n"
            + f"Then retry: erk land {pr_number}"
        )
        raise SystemExit(1)

    # Check for unresolved comments BEFORE merge
    check_unresolved_comments(ctx, main_repo_root, pr_number, force=force)

    # Merge the PR via GitHub API
    user_output(f"Merging PR #{pr_number}...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body or None
    merge_result = ctx.github.merge_pr(main_repo_root, pr_number, subject=subject, body=body)

    if merge_result is not True:
        error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
        user_output(
            click.style("Error: ", fg="red") + f"Failed to merge PR #{pr_number}\n\n{error_detail}"
        )
        raise SystemExit(1)

    user_output(click.style("✓", fg="green") + f" Merged PR #{pr_number} [{branch}]")

    # Check and display plan issue closure
    check_and_display_plan_issue_closure(ctx, main_repo_root, branch, pr_body=pr_details.body or "")

    # Check for linked objective and offer to update
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch)
    if objective_number is not None:
        prompt_objective_update(
            ctx,
            repo_root=main_repo_root,
            objective_number=objective_number,
            pr_number=pr_number,
            branch=branch,
            force=force,
        )

    # Cleanup and navigate (autolearn happens inside after confirmation)
    _cleanup_and_navigate(
        ctx,
        repo=repo,
        branch=branch,
        worktree_path=worktree_path,
        script=script,
        pull_flag=pull_flag,
        force=force,
        is_current_branch=is_current_branch,
        target_child_branch=None,
        objective_number=objective_number,
        no_delete=no_delete,
        autolearn=autolearn,
        pr_number=pr_number,
    )


def _land_by_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    force: bool,
    pull_flag: bool,
    branch_name: str,
    autolearn: bool,
    no_delete: bool,
) -> None:
    """Land a PR for a specific branch."""
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Look up PR for branch
    pr_details = ctx.github.get_pr_for_branch(main_repo_root, branch_name)

    if isinstance(pr_details, PRNotFound):
        user_output(
            click.style("Error: ", fg="red") + f"No pull request found for branch '{branch_name}'."
        )
        raise SystemExit(1)

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
    if pr_details.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request #{pr_number} is not open (state: {pr_details.state})."
        )
        raise SystemExit(1)

    # Validate PR base is trunk
    trunk = ctx.git.detect_trunk_branch(main_repo_root)
    if pr_details.base_ref_name != trunk:
        user_output(
            click.style("Error: ", fg="red")
            + f"PR #{pr_number} targets '{pr_details.base_ref_name}' "
            + f"but should target '{trunk}'.\n\n"
            + "The GitHub PR's base branch has diverged from your local stack.\n"
            + "Run: gt restack && gt submit\n"
            + f"Then retry: erk land {branch_name}"
        )
        raise SystemExit(1)

    # Check for unresolved comments BEFORE merge
    check_unresolved_comments(ctx, main_repo_root, pr_number, force=force)

    # Merge the PR via GitHub API
    user_output(f"Merging PR #{pr_number} for branch '{branch_name}'...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body or None
    merge_result = ctx.github.merge_pr(main_repo_root, pr_number, subject=subject, body=body)

    if merge_result is not True:
        error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
        user_output(
            click.style("Error: ", fg="red") + f"Failed to merge PR #{pr_number}\n\n{error_detail}"
        )
        raise SystemExit(1)

    user_output(click.style("✓", fg="green") + f" Merged PR #{pr_number} [{branch_name}]")

    # Check and display plan issue closure
    check_and_display_plan_issue_closure(
        ctx, main_repo_root, branch_name, pr_body=pr_details.body or ""
    )

    # Check for linked objective and offer to update
    objective_number = get_objective_for_branch(ctx, main_repo_root, branch_name)
    if objective_number is not None:
        prompt_objective_update(
            ctx,
            repo_root=main_repo_root,
            objective_number=objective_number,
            pr_number=pr_number,
            branch=branch_name,
            force=force,
        )

    # Cleanup and navigate (autolearn happens inside after confirmation)
    _cleanup_and_navigate(
        ctx,
        repo=repo,
        branch=branch_name,
        worktree_path=worktree_path,
        script=script,
        pull_flag=pull_flag,
        force=force,
        is_current_branch=is_current_branch,
        target_child_branch=None,
        objective_number=objective_number,
        no_delete=no_delete,
        autolearn=autolearn,
        pr_number=pr_number,
    )
