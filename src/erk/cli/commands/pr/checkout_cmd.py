"""Checkout a pull request or plan into a worktree.

This command fetches PR code (or finds plan branches) and creates a worktree
for local review/testing.

Routing:
- Plain number (123) or PR URL → PR checkout
- P-prefixed (P123) or issue URL → plan checkout (find branches/PRs for plan)
"""

import click
from rich.console import Console
from rich.table import Table

from erk.cli.activation import (
    activation_config_activate_only,
    ensure_worktree_activate_script,
    print_activation_instructions,
)
from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import (
    ensure_branch_has_worktree,
    navigate_and_display_checkout,
)
from erk.cli.commands.pr.dispatch_helpers import sync_branch_to_sha
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.gateway.github.parsing import (
    parse_plan_number_from_url,
    parse_pr_number_from_url,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.output.output import user_output


class _PrRef:
    """Parsed PR reference (plain number or PR URL)."""

    def __init__(self, number: int) -> None:
        self.number = number


class _PlanRef:
    """Parsed plan reference (P-prefix or issue URL)."""

    def __init__(self, number: int) -> None:
        self.number = number


def _parse_checkout_reference(reference: str) -> _PrRef | _PlanRef:
    """Parse checkout reference into PR or plan reference.

    Routing:
    - P-prefix (P123, p123) → plan
    - Issue URL (github.com/.../issues/N) → plan
    - PR URL (github.com/.../pull/N) → PR
    - Plain number (123) → PR

    Raises SystemExit(1) on invalid input.
    """
    # P-prefixed → plan
    if reference.upper().startswith("P") and reference[1:].isdigit():
        return _PlanRef(int(reference[1:]))

    # Plain number → PR
    if reference.isdigit():
        return _PrRef(int(reference))

    # GitHub issue URL → plan
    plan_number = parse_plan_number_from_url(reference)
    if plan_number is not None:
        return _PlanRef(plan_number)

    # GitHub PR URL → PR
    pr_number = parse_pr_number_from_url(reference)
    if pr_number is not None:
        return _PrRef(pr_number)

    user_output(
        click.style("Error: ", fg="red")
        + f"Invalid PR number, plan ID, or URL: {reference}\n\n"
        + "Expected formats:\n"
        + "  PR:   123 or https://github.com/owner/repo/pull/123\n"
        + "  Plan: P123 or https://github.com/owner/repo/issues/123"
    )
    raise SystemExit(1)


def _fetch_and_update_branch(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str,
    pr_number: int,
) -> None:
    """Fetch a branch from remote and update the local copy.

    Handles three cases:
    - Remote branch exists, no local branch: create tracking branch
    - Remote branch exists, local branch exists: force-update local to match remote
    - No remote branch, no local branch: fetch via PR ref
    """
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    remote_branches = ctx.git.branch.list_remote_branches(repo.root)
    remote_ref = f"origin/{branch_name}"
    if remote_ref in remote_branches:
        ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)
        if branch_name not in local_branches:
            ctx.branch_manager.create_tracking_branch(repo.root, branch_name, remote_ref)
        else:
            # Force-update local branch to match remote.
            # Uses ctx.git.branch directly because branch_manager.create_branch()
            # doesn't support force=True — this is an alignment operation, not
            # a new branch creation.
            ctx.git.branch.create_branch(repo.root, branch_name, remote_ref, force=True)
    elif branch_name not in local_branches:
        ctx.git.remote.fetch_pr_ref(
            repo_root=repo.root,
            remote="origin",
            pr_number=pr_number,
            local_branch=branch_name,
        )


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("reference")
@click.option("--no-slot", is_flag=True, help="Create worktree without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def pr_checkout(ctx: ErkContext, reference: str, no_slot: bool, force: bool, script: bool) -> None:
    """Checkout PR or plan into a worktree for review.

    REFERENCE can be:

    \b
    PR references:
      123                                    Plain PR number
      https://github.com/owner/repo/pull/123 GitHub PR URL

    \b
    Plan references:
      P123                                      Plan ID (P-prefix)
      https://github.com/owner/repo/issues/123  GitHub issue URL

    \b
    Examples:
        erk pr checkout 123       # Checkout PR #123
        erk pr checkout P456      # Find branches/PRs for plan #456
        erk pr co 123             # Short alias
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    ref = _parse_checkout_reference(reference)

    if isinstance(ref, _PlanRef):
        _checkout_plan(
            ctx, repo, plan_number=ref.number, no_slot=no_slot, force=force, script=script
        )
    else:
        _checkout_pr(ctx, repo, pr_number=ref.number, no_slot=no_slot, force=force, script=script)


# =============================================================================
# PR checkout (existing behavior)
# =============================================================================


def _checkout_pr(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    no_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Checkout a pull request into a worktree."""
    # Get PR details from GitHub
    ctx.console.info(f"Fetching PR #{pr_number}...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr, PRNotFound):
        ctx.console.error(
            f"Could not find PR #{pr_number}\n\n"
            "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    # Warn for closed/merged PRs
    if pr.state != "OPEN":
        ctx.console.info(f"Warning: PR #{pr_number} is {pr.state}")

    # Determine branch name strategy
    # For cross-repository PRs (forks), use pr/<number> to avoid conflicts
    # For same-repository PRs, use the actual branch name
    if pr.is_cross_repository:
        branch_name = f"pr/{pr_number}"
    else:
        branch_name = pr.head_ref_name

    # Check if branch already exists in a worktree - handle immediately
    existing_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        navigate_and_display_checkout(
            ctx,
            worktree_path=existing_worktree,
            branch_name=branch_name,
            script=script,
            command_name="pr-checkout",
            already_existed=True,
            existing_message=f"PR #{pr_number} already checked out at {{styled_path}}",
            new_message="",  # Not used when already_existed=True
            script_message_existing=f'echo "Went to existing worktree for PR #{pr_number}"',
            script_message_new="",  # Not used when already_existed=True
            post_cd_commands=None,
        )
        # Print activation instructions for existing worktrees too
        if not script:
            script_path = ensure_worktree_activate_script(
                worktree_path=existing_worktree,
                post_create_commands=None,
            )
            print_activation_instructions(
                script_path,
                source_branch=None,
                force=False,
                config=activation_config_activate_only(),
                copy=True,
                same_worktree=False,
            )
        return

    # For cross-repository PRs, always fetch via refs/pull/<n>/head
    # For same-repo PRs, always fetch from remote and force-update local branch
    if pr.is_cross_repository:
        ctx.git.remote.fetch_pr_ref(
            repo_root=repo.root, remote="origin", pr_number=pr_number, local_branch=branch_name
        )
    else:
        _fetch_and_update_branch(ctx, repo, branch_name=branch_name, pr_number=pr_number)

    # Create worktree using shared helper
    worktree_path, already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=no_slot, force=force
    )

    # For stacked PRs (base is not trunk), rebase onto base branch
    # This ensures git history includes the base branch as an ancestor,
    # which `gt track` requires for proper stacking
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo.root)
    if pr.base_ref_name != trunk_branch and not pr.is_cross_repository:
        local_branches = ctx.git.branch.list_local_branches(repo.root)
        if pr.base_ref_name not in local_branches:
            ctx.console.info(f"Fetching base branch '{pr.base_ref_name}'...")
            ctx.git.remote.fetch_branch(repo.root, "origin", pr.base_ref_name)
            ctx.branch_manager.create_tracking_branch(
                repo.root, pr.base_ref_name, f"origin/{pr.base_ref_name}"
            )
        else:
            # Parent exists locally but may be stale after squash/rebase.
            # Update to match origin so gt track sees consistent history.
            ctx.git.remote.fetch_branch(repo.root, "origin", pr.base_ref_name)
            remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{pr.base_ref_name}")
            local_sha = ctx.git.branch.get_branch_head(repo.root, pr.base_ref_name)
            if remote_sha is not None and remote_sha != local_sha:
                sync_branch_to_sha(ctx, repo.root, pr.base_ref_name, remote_sha)

        ctx.console.info("Rebasing onto base branch...")
        rebase_result = ctx.git.rebase.rebase_onto(worktree_path, f"origin/{pr.base_ref_name}")

        if not rebase_result.success:
            ctx.git.rebase.rebase_abort(worktree_path)
            ctx.console.info(
                f"Warning: Rebase had conflicts. Worktree created but needs manual rebase.\n"
                f"Run: cd {worktree_path} && git rebase origin/{pr.base_ref_name}"
            )

    # Graphite integration: Track or retrack AFTER rebase completes.
    # Tracking must happen after rebase so Graphite's cached SHA matches
    # the post-rebase commit, preventing divergence.
    should_track_with_graphite = (
        ctx.branch_manager.is_graphite_managed()
        and not already_existed
        and not pr.is_cross_repository
    )
    if should_track_with_graphite:
        if (
            ctx.graphite_branch_ops is not None
            and ctx.branch_manager.get_parent_branch(repo.root, branch_name) is not None
        ):
            # Already tracked — retrack to update Graphite's cached SHA
            ctx.graphite_branch_ops.retrack_branch(repo.root, branch_name)
        else:
            ctx.console.info("Tracking branch with Graphite...")
            ctx.branch_manager.track_branch(repo.root, branch_name, pr.base_ref_name)

    # Navigate and display checkout result
    navigate_and_display_checkout(
        ctx,
        worktree_path=worktree_path,
        branch_name=branch_name,
        script=script,
        command_name="pr-checkout",
        already_existed=already_existed,
        existing_message=f"PR #{pr_number} already checked out at {{styled_path}}",
        new_message=f"Created worktree for PR #{pr_number} at {{styled_path}}",
        script_message_existing=f'echo "Went to existing worktree for PR #{pr_number}"',
        script_message_new=f'echo "Checked out PR #{pr_number} at $(pwd)"',
        post_cd_commands=None,
    )

    # Print activation instructions (non-script mode only)
    # In script mode, shell integration handles navigation automatically
    if not script:
        script_path = ensure_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=None,
        )
        print_activation_instructions(
            script_path,
            source_branch=None,
            force=False,
            config=activation_config_activate_only(),
            copy=True,
            same_worktree=False,
        )


# =============================================================================
# Plan checkout (merged from plan/checkout_cmd.py)
# =============================================================================


def _checkout_plan(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    plan_number: int,
    no_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Checkout a branch associated with a plan.

    Plan IDs are no longer encoded in branch names, so we look up PRs
    referencing the plan issue directly.

    1. If single open PR -> fetch and checkout
    2. If multiple open PRs -> display table, no interactive selection
    3. If no open PRs -> display helpful message
    """
    prs = ctx.issues.get_prs_referencing_issue(repo.root, plan_number)

    # Filter to OPEN PRs only
    open_prs = [pr for pr in prs if pr.state == "OPEN"]

    if len(open_prs) == 0:
        user_output(
            f"No open PR found for plan #{plan_number}\n\n"
            "This plan has not been implemented yet. To prepare it:\n"
            f"  erk br co --for-plan {plan_number}\n\n"
            "Or if you've already checked out the branch:\n"
            f"  erk pr prepare {plan_number}"
        )
        raise SystemExit(1)

    if len(open_prs) == 1:
        # Single PR - fetch and checkout
        pr = open_prs[0]
        _checkout_plan_pr(
            ctx,
            repo,
            pr_number=pr.number,
            plan_number=plan_number,
            no_slot=no_slot,
            force=force,
            script=script,
        )
        return

    # Multiple open PRs - display table and exit
    _display_multiple_prs(plan_number, open_prs)
    raise SystemExit(0)


def _checkout_plan_pr(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    pr_number: int,
    plan_number: int,
    no_slot: bool,
    force: bool,
    script: bool,
) -> None:
    """Fetch and checkout a PR that references the plan issue."""
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
            existing_message=f"Plan #{plan_number} already checked out at {{styled_path}}",
            new_message="",  # Not used when already_existed=True
            script_message_existing=f'echo "Went to worktree for plan #{plan_number}"',
            script_message_new="",  # Not used when already_existed=True
            post_cd_commands=None,
        )
        return

    # Fetch from remote and force-update local branch
    _fetch_and_update_branch(ctx, repo, branch_name=branch_name, pr_number=pr_number)

    # Create worktree and navigate
    worktree_path, already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=no_slot, force=force
    )

    new_msg = f"Created worktree for plan #{plan_number} (PR #{pr_number}) at {{styled_path}}"
    navigate_and_display_checkout(
        ctx,
        worktree_path=worktree_path,
        branch_name=branch_name,
        script=script,
        command_name="plan-checkout",
        already_existed=already_existed,
        existing_message=f"Plan #{plan_number} already checked out at {{styled_path}}",
        new_message=new_msg,
        script_message_existing=f'echo "Went to worktree for plan #{plan_number}"',
        script_message_new=f'echo "Checked out plan #{plan_number} (PR #{pr_number}) at $(pwd)"',
        post_cd_commands=None,
    )


def _display_multiple_prs(plan_number: int, prs) -> None:
    """Display table of multiple PRs for a plan."""
    user_output(f"Multiple open PRs found for plan #{plan_number}:\n")

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

    user_output("Use erk pr checkout to checkout a specific PR:\n  erk pr checkout <pr-number>")
