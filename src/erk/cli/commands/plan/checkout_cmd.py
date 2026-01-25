"""Checkout a branch associated with a plan.

This command finds and checks out local branches or fetches PRs
that are associated with a given plan identifier.
"""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.commands.checkout_helpers import (
    ensure_branch_has_worktree,
    navigate_and_display_checkout,
)
from erk.cli.ensure import Ensure
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_output


def _find_branches_for_issue(
    ctx: ErkContext,
    repo_root,
    issue_number: int,
) -> list[str]:
    """Find local branches that start with the issue number.

    Branch names follow patterns like:
    - P{issue_number}-{slug}-{timestamp} (e.g., P123-fix-bug-01-15-1430)
    - {issue_number}-{slug} (legacy format)

    Args:
        ctx: Erk context with git integration
        repo_root: Repository root path
        issue_number: Issue number to match

    Returns:
        List of matching branch names
    """
    local_branches = ctx.git.list_local_branches(repo_root)
    matching: list[str] = []

    for branch in local_branches:
        branch_issue = extract_leading_issue_number(branch)
        if branch_issue == issue_number:
            matching.append(branch)

    return matching


@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("identifier", type=str)
@click.option("--no-slot", is_flag=True, help="Create worktree without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def checkout_plan(
    ctx: ErkContext,
    identifier: str,
    no_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Checkout a branch associated with a plan.

    IDENTIFIER can be:
    - Plain number: 123
    - P-prefixed: P123
    - GitHub URL: https://github.com/owner/repo/issues/123

    Behavior:
    1. If local branch exists -> checkout (or navigate to existing worktree)
    2. If no local branch but has PR -> fetch PR and create tracking branch
    3. If multiple branches/PRs -> display table, no interactive selection
    4. If no branches/PRs -> display helpful message

    Examples:

        # Checkout by plan ID
        erk plan co P123

        # Checkout by plain number
        erk plan co 123

        # Checkout by GitHub URL
        erk plan co https://github.com/owner/repo/issues/123
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Parse identifier (handles plain numbers, P-prefixed, and URLs)
    issue_number = parse_issue_identifier(identifier)

    # Find local branches for this issue
    local_branches = _find_branches_for_issue(ctx, repo.root, issue_number)

    # Case 1: Single local branch found
    if len(local_branches) == 1:
        branch_name = local_branches[0]
        _checkout_branch(
            ctx,
            repo,
            branch_name=branch_name,
            issue_number=issue_number,
            no_slot=no_slot,
            force=force,
            script=script,
        )
        return

    # Case 2: Multiple local branches found - display table and exit
    if len(local_branches) > 1:
        _display_multiple_branches(issue_number, local_branches)
        raise SystemExit(0)

    # Case 3: No local branches - check for PRs
    prs = ctx.issues.get_prs_referencing_issue(repo.root, issue_number)

    # Filter to OPEN PRs only
    open_prs = [pr for pr in prs if pr.state == "OPEN"]

    if len(open_prs) == 0:
        # No local branches and no open PRs
        user_output(
            f"No local branch or open PR found for plan #{issue_number}\n\n"
            "This plan has not been implemented yet. To prepare it:\n"
            f"  • Run: erk prepare {issue_number}"
        )
        raise SystemExit(1)

    if len(open_prs) == 1:
        # Single PR - fetch and checkout
        pr = open_prs[0]
        _checkout_pr(
            ctx,
            repo,
            pr_number=pr.number,
            issue_number=issue_number,
            no_slot=no_slot,
            force=force,
            script=script,
        )
        return

    # Multiple open PRs - display table and exit
    _display_multiple_prs(issue_number, open_prs)
    raise SystemExit(0)


def _checkout_branch(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str,
    issue_number: int,
    no_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Checkout an existing local branch."""
    worktree_path, already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=no_slot, force=force
    )

    navigate_and_display_checkout(
        ctx,
        worktree_path=worktree_path,
        branch_name=branch_name,
        script=script,
        command_name="plan-checkout",
        already_existed=already_existed,
        existing_message=f"Plan #{issue_number} already checked out at {{styled_path}}",
        new_message=f"Created worktree for plan #{issue_number} at {{styled_path}}",
        script_message_existing=f'echo "Went to worktree for plan #{issue_number}"',
        script_message_new=f'echo "Checked out plan #{issue_number} at $(pwd)"',
    )


def _checkout_pr(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    issue_number: int,
    no_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Fetch and checkout a PR that references the plan issue."""
    from erk_shared.github.types import PRNotFound

    # Get PR details
    ctx.console.info(f"Fetching PR #{pr_number}...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr, PRNotFound):
        ctx.console.error(
            f"Could not find PR #{pr_number}\n\n"
            "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    branch_name = pr.head_ref_name

    # Check if branch already exists in a worktree - handle this case immediately
    existing_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        navigate_and_display_checkout(
            ctx,
            worktree_path=existing_worktree,
            branch_name=branch_name,
            script=script,
            command_name="plan-checkout",
            already_existed=True,
            existing_message=f"Plan #{issue_number} already checked out at {{styled_path}}",
            new_message="",  # Not used when already_existed=True
            script_message_existing=f'echo "Went to worktree for plan #{issue_number}"',
            script_message_new="",  # Not used when already_existed=True
        )
        return

    # Fetch the branch from remote if not local
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name not in local_branches:
        remote_branches = ctx.git.list_remote_branches(repo.root)
        remote_ref = f"origin/{branch_name}"
        if remote_ref in remote_branches:
            ctx.git.fetch_branch(repo.root, "origin", branch_name)
            ctx.branch_manager.create_tracking_branch(repo.root, branch_name, remote_ref)
        else:
            ctx.git.fetch_pr_ref(
                repo_root=repo.root,
                remote="origin",
                pr_number=pr_number,
                local_branch=branch_name,
            )

    # Create worktree and navigate
    worktree_path, already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=no_slot, force=force
    )

    new_msg = f"Created worktree for plan #{issue_number} (PR #{pr_number}) at {{styled_path}}"
    navigate_and_display_checkout(
        ctx,
        worktree_path=worktree_path,
        branch_name=branch_name,
        script=script,
        command_name="plan-checkout",
        already_existed=already_existed,
        existing_message=f"Plan #{issue_number} already checked out at {{styled_path}}",
        new_message=new_msg,
        script_message_existing=f'echo "Went to worktree for plan #{issue_number}"',
        script_message_new=f'echo "Checked out plan #{issue_number} (PR #{pr_number}) at $(pwd)"',
    )


def _display_multiple_branches(issue_number: int, branches: list[str]) -> None:
    """Display table of multiple branches for an issue."""
    user_output(f"Multiple branches found for plan #{issue_number}:\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("branch", style="yellow", no_wrap=True)

    for branch in sorted(branches):
        table.add_row(branch)

    console = Console(stderr=True, width=200)
    console.print(table)
    console.print()

    user_output(
        "Use git checkout or erk wt create to checkout a specific branch:\n"
        "  • erk wt create <branch-name>"
    )


def _display_multiple_prs(issue_number: int, prs) -> None:
    """Display table of multiple PRs for an issue."""
    user_output(f"Multiple open PRs found for plan #{issue_number}:\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("pr", style="cyan", no_wrap=True)
    table.add_column("state", no_wrap=True)
    table.add_column("draft", no_wrap=True)

    for pr in prs:
        state_color = "green" if pr.state == "OPEN" else "red"
        state_text = f"[{state_color}]{pr.state}[/{state_color}]"
        draft_text = "[dim]yes[/dim]" if pr.is_draft else "-"
        table.add_row(f"#{pr.number}", state_text, draft_text)

    console = Console(stderr=True, width=200)
    console.print(table)
    console.print()

    user_output("Use erk pr checkout to checkout a specific PR:\n  • erk pr checkout <pr-number>")
