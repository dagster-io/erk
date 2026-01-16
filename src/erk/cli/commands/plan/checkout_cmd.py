"""Checkout the branch associated with a plan."""

from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import display_sync_status, navigate_to_worktree
from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.issues.types import PRReference
from erk_shared.github.metadata.plan_header import extract_plan_header_worktree_name
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


def _find_local_branches_for_plan(
    ctx: ErkContext,
    *,
    repo_root: Path,
    issue_number: int,
    worktree_name: str | None,
) -> list[str]:
    """Find local branches that match the plan pattern.

    Looks for branches matching P{issue_number}-* pattern.
    Also includes worktree_name if set and not already matched.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        issue_number: Plan issue number
        worktree_name: Optional worktree name from plan metadata

    Returns:
        List of matching branch names
    """
    local_branches = ctx.git.list_local_branches(repo_root)
    prefix = f"P{issue_number}-"

    matches: list[str] = []
    for branch in local_branches:
        if branch.startswith(prefix):
            matches.append(branch)

    # Add worktree_name if set and not already in matches
    if worktree_name is not None and worktree_name not in matches:
        if worktree_name in local_branches:
            matches.append(worktree_name)

    return matches


def _filter_open_prs(pr_refs: list[PRReference]) -> list[PRReference]:
    """Filter to only OPEN PRs.

    Args:
        pr_refs: List of PR references

    Returns:
        List of PRReferences with state "OPEN"
    """
    return [pr for pr in pr_refs if pr.state == "OPEN"]


def _display_multiple_branches(branches: list[str], issue_number: int) -> None:
    """Display message when multiple local branches exist.

    Args:
        branches: List of branch names
        issue_number: Plan issue number
    """
    user_output(f"Plan #{issue_number} has multiple local branches:")
    user_output("")
    for branch in sorted(branches):
        user_output(f"  {branch}")
    user_output("")
    user_output("Checkout a specific branch with: erk br co <branch>")


def _display_multiple_prs(
    ctx: ErkContext,
    *,
    repo_root: Path,
    open_prs: list[PRReference],
    issue_number: int,
) -> None:
    """Display table when multiple open PRs exist.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        open_prs: List of open PR references
        issue_number: Plan issue number
    """
    user_output(f"Plan #{issue_number} has multiple open PRs:")
    user_output("")

    # Header
    header = f"{'PR':<10}{'State':<10}{'Branch':<30}Title"
    user_output(header)

    # Get PR details for branch and title
    for pr_ref in open_prs:
        pr_details = ctx.github.get_pr(repo_root, pr_ref.number)
        if isinstance(pr_details, PRNotFound):
            # Skip PRs we can't fetch details for
            continue

        state = "DRAFT" if pr_ref.is_draft else "OPEN"
        head_ref = pr_details.head_ref_name
        branch = head_ref[:28] if len(head_ref) > 28 else head_ref
        title = pr_details.title[:40] if len(pr_details.title) > 40 else pr_details.title
        row = f"#{pr_ref.number:<9}{state:<10}{branch:<30}{title}"
        user_output(row)

    user_output("")
    user_output("Checkout a specific PR with: erk pr co <pr_number>")


def _checkout_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    branch_name: str,
    issue_number: int,
    force: bool,
    script: bool,
) -> None:
    """Checkout a branch into a worktree.

    Uses slot allocation to manage worktree.

    Args:
        ctx: Erk context
        repo: Repository context
        branch_name: Branch to checkout
        issue_number: Plan issue number (for display)
        force: Auto-unassign oldest if pool full
        script: Script mode flag
    """
    # Check if branch already exists in a worktree
    existing_worktree = ctx.git.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        # Branch already checked out - navigate to it
        styled_path = click.style(str(existing_worktree), fg="cyan", bold=True)
        should_output = navigate_to_worktree(
            ctx,
            worktree_path=existing_worktree,
            branch=branch_name,
            script=script,
            command_name="plan-checkout",
            script_message=f'echo "Went to existing worktree for plan #{issue_number}"',
            relative_path=None,
            post_cd_commands=None,
        )
        if should_output:
            user_output(f"Plan #{issue_number} already checked out at {styled_path}")
            display_sync_status(
                ctx, worktree_path=existing_worktree, branch=branch_name, script=script
            )
        return

    # Branch exists but not in a worktree - allocate slot
    result = allocate_slot_for_branch(
        ctx,
        repo,
        branch_name,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )
    worktree_path = result.worktree_path

    if not result.already_assigned:
        user_output(click.style(f"✓ Assigned {branch_name} to {result.slot_name}", fg="green"))

    # Navigate to the worktree
    styled_path = click.style(str(worktree_path), fg="cyan", bold=True)
    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch_name,
        script=script,
        command_name="plan-checkout",
        script_message=f'echo "Checked out plan #{issue_number} at $(pwd)"',
        relative_path=None,
        post_cd_commands=None,
    )
    if should_output:
        user_output(f"Checked out plan #{issue_number} at {styled_path}")
        display_sync_status(ctx, worktree_path=worktree_path, branch=branch_name, script=script)


def _checkout_pr_branch(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    pr_number: int,
    issue_number: int,
    force: bool,
    script: bool,
) -> None:
    """Checkout a PR branch into a worktree.

    Fetches the PR branch if needed and creates a worktree.

    Args:
        ctx: Erk context
        repo: Repository context
        pr_number: PR number to checkout
        issue_number: Plan issue number (for display)
        force: Auto-unassign oldest if pool full
        script: Script mode flag
    """
    # Get PR details
    pr = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr, PRNotFound):
        user_output(click.style("Error: ", fg="red") + f"Could not find PR #{pr_number}")
        raise SystemExit(1)

    branch_name = pr.head_ref_name

    # Check if branch already exists in a worktree
    existing_worktree = ctx.git.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        # Already checked out - navigate
        styled_path = click.style(str(existing_worktree), fg="cyan", bold=True)
        should_output = navigate_to_worktree(
            ctx,
            worktree_path=existing_worktree,
            branch=branch_name,
            script=script,
            command_name="plan-checkout",
            script_message=f'echo "Went to existing worktree for plan #{issue_number}"',
            relative_path=None,
            post_cd_commands=None,
        )
        if should_output:
            user_output(f"Plan #{issue_number} already checked out at {styled_path}")
            display_sync_status(
                ctx, worktree_path=existing_worktree, branch=branch_name, script=script
            )
        return

    # Fetch PR branch if not local
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name not in local_branches:
        if pr.is_cross_repository:
            # Fetch via PR ref for forks
            ctx.git.fetch_pr_ref(
                repo_root=repo.root,
                remote="origin",
                pr_number=pr_number,
                local_branch=branch_name,
            )
        else:
            # Same repo - fetch and create tracking branch
            remote_branches = ctx.git.list_remote_branches(repo.root)
            remote_ref = f"origin/{branch_name}"
            if remote_ref in remote_branches:
                ctx.git.fetch_branch(repo.root, "origin", branch_name)
                ctx.git.create_tracking_branch(repo.root, branch_name, remote_ref)
            else:
                # Branch not on remote, fetch via PR ref
                ctx.git.fetch_pr_ref(
                    repo_root=repo.root,
                    remote="origin",
                    pr_number=pr_number,
                    local_branch=branch_name,
                )

    # Allocate slot
    result = allocate_slot_for_branch(
        ctx,
        repo,
        branch_name,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )
    worktree_path = result.worktree_path

    if not result.already_assigned:
        user_output(click.style(f"✓ Assigned {branch_name} to {result.slot_name}", fg="green"))

    # Navigate
    styled_path = click.style(str(worktree_path), fg="cyan", bold=True)
    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch_name,
        script=script,
        command_name="plan-checkout",
        script_message=f'echo "Checked out plan #{issue_number} from PR #{pr_number} at $(pwd)"',
        relative_path=None,
        post_cd_commands=None,
    )
    if should_output:
        user_output(f"Checked out plan #{issue_number} from PR #{pr_number} at {styled_path}")
        display_sync_status(ctx, worktree_path=worktree_path, branch=branch_name, script=script)


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("plan_id", type=str)
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def plan_checkout(ctx: ErkContext, plan_id: str, force: bool, script: bool) -> None:
    """Checkout the branch associated with a plan.

    PLAN_ID can be a plain number (123) or GitHub issue URL
    (https://github.com/owner/repo/issues/123).

    Behavior:
      - If a local branch matching P{plan_id}-* exists, check it out
      - If multiple local branches match, display them and exit
      - If no local branch but a single open PR references the plan, check out the PR
      - If multiple open PRs, display them and exit
      - If no local branch and no open PRs, suggest 'erk plan implement'

    Examples:

        erk plan co 123                    # Checkout plan #123

        erk plan checkout 123 --force      # Auto-unassign if pool full
    """
    # Validate we're in a repo
    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    # Parse plan ID
    issue_number = parse_issue_identifier(plan_id)

    # Fetch plan to get worktree_name from metadata
    try:
        plan = ctx.plan_store.get_plan(repo.root, str(issue_number))
    except RuntimeError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "404" in error_msg:
            user_output(click.style("Error: ", fg="red") + f"Plan #{issue_number} not found")
        else:
            user_output(click.style("Error: ", fg="red") + error_msg)
        raise SystemExit(1) from None

    # Extract worktree_name from plan body
    worktree_name = extract_plan_header_worktree_name(plan.body)

    # Find matching local branches
    local_branches = _find_local_branches_for_plan(
        ctx,
        repo_root=repo.root,
        issue_number=issue_number,
        worktree_name=worktree_name,
    )

    # Decision tree
    if len(local_branches) == 1:
        # Single local branch - check it out
        _checkout_branch(
            ctx,
            repo=repo,
            branch_name=local_branches[0],
            issue_number=issue_number,
            force=force,
            script=script,
        )
        return

    if len(local_branches) > 1:
        # Multiple local branches - display and exit
        _display_multiple_branches(local_branches, issue_number)
        raise SystemExit(1)

    # No local branches - check for open PRs
    pr_refs = ctx.issues.get_prs_referencing_issue(repo.root, issue_number)
    open_prs = _filter_open_prs(pr_refs)

    if len(open_prs) == 1:
        # Single open PR - check it out
        _checkout_pr_branch(
            ctx,
            repo=repo,
            pr_number=open_prs[0].number,
            issue_number=issue_number,
            force=force,
            script=script,
        )
        return

    if len(open_prs) > 1:
        # Multiple open PRs - display and exit
        _display_multiple_prs(
            ctx,
            repo_root=repo.root,
            open_prs=open_prs,
            issue_number=issue_number,
        )
        raise SystemExit(1)

    # Neither local branch nor open PR exists
    user_output(f"Plan #{issue_number} has no local branch or open PR.")
    user_output("")
    user_output("To start implementing this plan, run:")
    user_output(f"  erk plan implement {issue_number}")
    raise SystemExit(1)
