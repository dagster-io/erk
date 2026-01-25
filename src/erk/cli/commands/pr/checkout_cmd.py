"""Checkout a pull request into a worktree.

This command fetches PR code and creates a worktree for local review/testing.
"""

import click

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
from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRNotFound


@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("pr_reference")
@click.option("--no-slot", is_flag=True, help="Create worktree without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def pr_checkout(
    ctx: ErkContext, pr_reference: str, no_slot: bool, force: bool, script: bool
) -> None:
    """Checkout PR into a worktree for review.

    PR_REFERENCE can be a plain number (123) or GitHub URL
    (https://github.com/owner/repo/pull/123).

    Examples:

        # Checkout by PR number
        erk pr checkout 123

        # Checkout by GitHub URL
        erk pr checkout https://github.com/owner/repo/pull/123
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    if isinstance(ctx.repo, NoRepoSentinel):
        ctx.console.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    pr_number = parse_pr_reference(pr_reference)

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
            )
        return

    # For cross-repository PRs, always fetch via refs/pull/<n>/head
    # For same-repo PRs, check if branch exists locally first
    if pr.is_cross_repository:
        ctx.git.fetch_pr_ref(
            repo_root=repo.root, remote="origin", pr_number=pr_number, local_branch=branch_name
        )
    else:
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

    # Create worktree using shared helper
    worktree_path, already_existed = ensure_branch_has_worktree(
        ctx, repo, branch_name=branch_name, no_slot=no_slot, force=force
    )

    # For stacked PRs (base is not trunk), rebase onto base branch
    # This ensures git history includes the base branch as an ancestor,
    # which `gt track` requires for proper stacking
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)
    if pr.base_ref_name != trunk_branch and not pr.is_cross_repository:
        local_branches = ctx.git.list_local_branches(repo.root)
        if pr.base_ref_name not in local_branches:
            ctx.console.info(f"Fetching base branch '{pr.base_ref_name}'...")
            ctx.git.fetch_branch(repo.root, "origin", pr.base_ref_name)
            ctx.branch_manager.create_tracking_branch(
                repo.root, pr.base_ref_name, f"origin/{pr.base_ref_name}"
            )

        ctx.console.info("Rebasing onto base branch...")
        rebase_result = ctx.git.rebase_onto(worktree_path, f"origin/{pr.base_ref_name}")

        if not rebase_result.success:
            ctx.git.rebase_abort(worktree_path)
            ctx.console.info(
                f"Warning: Rebase had conflicts. Worktree created but needs manual rebase.\n"
                f"Run: cd {worktree_path} && git rebase origin/{pr.base_ref_name}"
            )

    # Graphite integration: Track and submit if enabled (for new worktrees only)
    if (
        ctx.branch_manager.is_graphite_managed()
        and not already_existed
        and not pr.is_cross_repository
    ):
        parent = ctx.branch_manager.get_parent_branch(repo.root, branch_name)
        if parent is None:
            ctx.console.info("Tracking branch with Graphite...")
            ctx.branch_manager.track_branch(worktree_path, branch_name, pr.base_ref_name)
            ctx.console.info("Submitting to link with Graphite...")
            ctx.branch_manager.submit_branch(worktree_path, branch_name)
            ctx.console.info(click.style("✓", fg="green") + " Branch linked with Graphite")

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
        )
