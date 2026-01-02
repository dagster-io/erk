"""Land PR and delete worktree.

This command merges a PR and cleans up the worktree/branch.
It can operate on the current branch or a specified PR.

Usage:
    erk pr land          # Land current branch's PR
    erk pr land 123      # Land PR by number
    erk pr land <url>    # Land PR by URL
"""

import re
from dataclasses import replace
from pathlib import Path

import click

from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
    delete_branch_and_worktree,
)
from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.types import LandPrError, LandPrSuccess
from erk_shared.github.types import PRDetails, PRNotFound
from erk_shared.output.output import user_output


def parse_pr_or_url(pr_or_url: str) -> int | None:
    """Parse a PR number or URL, returning the PR number.

    Args:
        pr_or_url: Either a PR number (e.g., "123") or a GitHub PR URL

    Returns:
        PR number if parsed successfully, None if invalid format
    """
    # Try parsing as a plain number
    if pr_or_url.isdigit():
        return int(pr_or_url)

    # Try parsing as a GitHub PR URL
    # Handles: https://github.com/owner/repo/pull/123
    match = re.search(r"/pull/(\d+)", pr_or_url)
    if match:
        return int(match.group(1))

    return None


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


def _cleanup_and_navigate(
    ctx: ErkContext,
    repo: RepoContext,
    branch: str,
    worktree_path: Path | None,
    script: bool,
    pull_flag: bool,
    force: bool,
    is_current_branch: bool,
    target_child_branch: str | None,
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
    """
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    if worktree_path is not None:
        # Confirm cleanup unless --force
        if not force:
            if not click.confirm(f"Delete worktree and branch '{branch}'?", default=True, err=True):
                user_output("Worktree preserved. Branch still exists locally.")
                # Still need to navigate if we're in the worktree being preserved
                if is_current_branch:
                    _navigate_after_land(ctx, repo, script, pull_flag, target_child_branch=None)
                return

        delete_branch_and_worktree(ctx, repo, branch, worktree_path)
        user_output(click.style("✓", fg="green") + " Deleted worktree and branch")
    else:
        # No worktree - check if branch exists locally before deletion (LBYL)
        local_branches = ctx.git.list_local_branches(main_repo_root)
        if branch in local_branches:
            ctx.git.delete_branch_with_graphite(main_repo_root, branch, force=True)
            user_output(click.style("✓", fg="green") + f" Deleted branch '{branch}'")
        else:
            # Branch doesn't exist locally (fork PR case)
            user_output(click.style("ℹ", fg="cyan") + f" Branch '{branch}' not found locally")

    # Navigate (only if we were in the deleted worktree)
    if is_current_branch:
        _navigate_after_land(ctx, repo, script, pull_flag, target_child_branch)


def _navigate_after_land(
    ctx: ErkContext,
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
        # Suggest running gt restack to update child branch's PR base
        user_output(
            click.style("💡", fg="cyan")
            + f" Run 'gt restack' in {target_child_branch} to update PR base branch"
        )
        activate_worktree(ctx, post_deletion_repo, target_path, script, command_name="pr-land")
        # activate_worktree raises SystemExit(0)
    else:
        # Construct git pull commands if pull_flag is set
        post_commands: list[str] | None = None
        if pull_flag:
            trunk_branch = ctx.git.detect_trunk_branch(main_repo_root)
            post_commands = [
                f'__erk_log "->" "git pull origin {trunk_branch}"',
                f"git pull --ff-only origin {trunk_branch} || "
                f'echo "Warning: git pull failed (try running manually)" >&2',
            ]
        # Output activation script pointing to trunk/root repo
        activate_root_repo(
            ctx, post_deletion_repo, script, command_name="pr-land", post_cd_commands=post_commands
        )
        # activate_root_repo raises SystemExit(0)


@click.command("land", cls=CommandWithHiddenOptions)
@script_option
@click.argument("pr_or_url", required=False)
@click.option(
    "--up",
    "up_flag",
    is_flag=True,
    help="Navigate to child branch instead of trunk after landing",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip cleanup confirmation prompt",
)
@click.option(
    "--pull/--no-pull",
    "pull_flag",
    default=True,
    help="Pull latest changes after landing (default: --pull)",
)
@click.pass_obj
def pr_land(
    ctx: ErkContext,
    script: bool,
    pr_or_url: str | None,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
) -> None:
    """Merge PR and delete worktree.

    Can land the current branch's PR or a specific PR by number/URL.

    \b
    Usage:
      erk pr land          # Land current branch's PR
      erk pr land 123      # Land PR #123
      erk pr land <url>    # Land PR by GitHub URL

    With shell integration (recommended):
      erk pr land

    Without shell integration:
      source <(erk pr land --script)

    Requires:
    - Graphite enabled: 'erk config set use_graphite true'
    - PR must be open and ready to merge
    - PR's base branch must be trunk (one level from trunk)
    """
    # Validate prerequisites
    Ensure.gh_authenticated(ctx)
    Ensure.graphite_available(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)

    # Validate shell integration for activation script output
    if not script:
        user_output(
            click.style("Error: ", fg="red")
            + "This command requires shell integration for activation.\n\n"
            + "Options:\n"
            + "  1. Use shell integration: erk pr land\n"
            + "     (Requires 'erk init --shell' setup)\n\n"
            + "  2. Use --script flag: source <(erk pr land --script)\n"
        )
        raise SystemExit(1)

    # Determine if landing current branch or a specific PR
    if pr_or_url is None:
        # Landing current branch's PR (original behavior)
        _land_current_branch(ctx, repo, script, up_flag, force, pull_flag)
    else:
        # Landing a specific PR by number or URL
        _land_specific_pr(ctx, repo, script, up_flag, force, pull_flag, pr_or_url)


def _land_current_branch(
    ctx: ErkContext,
    repo: RepoContext,
    script: bool,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
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
        children = ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch)
        if len(children) == 0:
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has no children.\n"
                "Use 'erk pr land' without --up to return to trunk."
            )
            raise SystemExit(1)
        elif len(children) > 1:
            children_list = ", ".join(f"'{c}'" for c in children)
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot use --up: branch '{current_branch}' has multiple children: "
                f"{children_list}.\n"
                "Use 'erk pr land' without --up, then 'erk co <branch>' to choose."
            )
            raise SystemExit(1)
        else:
            target_child_branch = children[0]

    # Step 1: Execute land-pr (merges the PR)
    # render_events() uses click.echo() + sys.stderr.flush() for immediate unbuffered output
    result = render_events(execute_land_pr(ctx, ctx.cwd))

    if isinstance(result, LandPrError):
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1)

    # Success - PR was merged
    success_result: LandPrSuccess = result
    user_output(
        click.style("✓", fg="green")
        + f" Merged PR #{success_result.pr_number} [{success_result.branch_name}]"
    )

    # Step 2: Cleanup and navigate
    _cleanup_and_navigate(
        ctx,
        repo,
        current_branch,
        current_worktree_path,
        script,
        pull_flag,
        force,
        is_current_branch=True,
        target_child_branch=target_child_branch,
    )


def _land_specific_pr(
    ctx: ErkContext,
    repo: RepoContext,
    script: bool,
    up_flag: bool,
    force: bool,
    pull_flag: bool,
    pr_or_url: str,
) -> None:
    """Land a specific PR by number or URL."""
    # Validate --up is not used with PR argument
    if up_flag:
        user_output(
            click.style("Error: ", fg="red") + "Cannot use --up when specifying a PR.\n"
            "The --up flag only works when landing the current branch's PR."
        )
        raise SystemExit(1)

    # Parse PR number from argument
    pr_number = parse_pr_or_url(pr_or_url)
    if pr_number is None:
        user_output(
            click.style("Error: ", fg="red") + f"Invalid PR identifier: {pr_or_url}\n"
            "Expected a PR number (e.g., 123) or GitHub URL."
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
            + f"Then retry: erk pr land {pr_number}"
        )
        raise SystemExit(1)

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

    # Cleanup and navigate
    _cleanup_and_navigate(
        ctx,
        repo,
        branch,
        worktree_path,
        script,
        pull_flag,
        force,
        is_current_branch,
        target_child_branch=None,
    )
