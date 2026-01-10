"""Checkout a pull request into a worktree.

This command fetches PR code and creates a worktree for local review/testing.
"""

import click

from erk.cli.alias import alias
from erk.cli.commands.checkout_helpers import navigate_to_worktree
from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference
from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import worktree_path_for
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


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

    # Check if branch already exists in a worktree
    existing_worktree = ctx.git.find_worktree_for_branch(repo.root, branch_name)
    if existing_worktree is not None:
        # Branch already exists in a worktree - activate it
        styled_path = click.style(str(existing_worktree), fg="cyan", bold=True)
        should_output = navigate_to_worktree(
            ctx,
            worktree_path=existing_worktree,
            branch=branch_name,
            script=script,
            command_name="pr-checkout",
            script_message=f'echo "Went to existing worktree for PR #{pr_number}"',
            relative_path=None,
            post_cd_commands=None,
        )
        if should_output:
            user_output(f"PR #{pr_number} already checked out at {styled_path}")
        return

    # For cross-repository PRs, always fetch via refs/pull/<n>/head
    # For same-repo PRs, check if branch exists locally first
    if pr.is_cross_repository:
        # Fetch PR ref directly
        ctx.git.fetch_pr_ref(
            repo_root=repo.root, remote="origin", pr_number=pr_number, local_branch=branch_name
        )
    else:
        # Check if branch exists locally or on remote
        local_branches = ctx.git.list_local_branches(repo.root)
        if branch_name in local_branches:
            # Branch already exists locally - just need to create worktree
            pass
        else:
            # Check remote and fetch if needed
            remote_branches = ctx.git.list_remote_branches(repo.root)
            remote_ref = f"origin/{branch_name}"
            if remote_ref in remote_branches:
                ctx.git.fetch_branch(repo.root, "origin", branch_name)
                ctx.git.create_tracking_branch(repo.root, branch_name, remote_ref)
            else:
                # Branch not on remote (maybe local-only PR?), fetch via PR ref
                ctx.git.fetch_pr_ref(
                    repo_root=repo.root,
                    remote="origin",
                    pr_number=pr_number,
                    local_branch=branch_name,
                )

    # Create worktree - use slot allocation unless --no-slot is specified
    if no_slot:
        # Old behavior: derive worktree path from branch name
        worktree_path = worktree_path_for(repo.worktrees_dir, branch_name)
        ctx.git.add_worktree(
            repo.root,
            worktree_path,
            branch=branch_name,
            ref=None,
            create_branch=False,
        )
    else:
        # New behavior: use slot allocation
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

    # For stacked PRs (base is not trunk), rebase onto base branch
    # This ensures git history includes the base branch as an ancestor,
    # which `gt track` requires for proper stacking
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)
    if pr.base_ref_name != trunk_branch and not pr.is_cross_repository:
        ctx.console.info(f"Fetching base branch '{pr.base_ref_name}'...")
        ctx.git.fetch_branch(repo.root, "origin", pr.base_ref_name)

        ctx.console.info("Rebasing onto base branch...")
        rebase_result = ctx.git.rebase_onto(worktree_path, f"origin/{pr.base_ref_name}")

        if not rebase_result.success:
            ctx.git.rebase_abort(worktree_path)
            ctx.console.info(
                f"Warning: Rebase had conflicts. Worktree created but needs manual rebase.\n"
                f"Run: cd {worktree_path} && git rebase origin/{pr.base_ref_name}"
            )

    # Navigate to the new worktree
    styled_path = click.style(str(worktree_path), fg="cyan", bold=True)
    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch_name,
        script=script,
        command_name="pr-checkout",
        script_message=f'echo "Checked out PR #{pr_number} at $(pwd)"',
        relative_path=None,
        post_cd_commands=None,
    )
    if should_output:
        user_output(f"Created worktree for PR #{pr_number} at {styled_path}")
