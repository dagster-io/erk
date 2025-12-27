"""Checkout a pull request into a worktree.

This command fetches PR code and creates a worktree for local review/testing.
"""

import click

from erk.cli.activation import render_activation_script
from erk.cli.alias import alias
from erk.cli.commands.pr.parse_pr_reference import parse_pr_reference
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
@script_option
@click.pass_obj
def pr_checkout(ctx: ErkContext, pr_reference: str, script: bool) -> None:
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
        ctx.feedback.error("Not in a git repository")
        raise SystemExit(1)
    repo: RepoContext = ctx.repo

    pr_number = parse_pr_reference(pr_reference)

    # Get PR details from GitHub
    ctx.feedback.info(f"Fetching PR #{pr_number}...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    if isinstance(pr, PRNotFound):
        ctx.feedback.error(
            f"Could not find PR #{pr_number}\n\n"
            "Check the PR number and ensure you're authenticated with gh CLI."
        )
        raise SystemExit(1)

    # Warn for closed/merged PRs
    if pr.state != "OPEN":
        ctx.feedback.info(f"Warning: PR #{pr_number} is {pr.state}")

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
        if script:
            activation_script = render_activation_script(
                worktree_path=existing_worktree,
                final_message=f'echo "Went to existing worktree for PR #{pr_number}"',
            )
            result = ctx.script_writer.write_activation_script(
                activation_script,
                command_name="pr-checkout",
                comment=f"activate PR #{pr_number}",
            )
            result.output_for_shell_integration()
        else:
            styled_path = click.style(str(existing_worktree), fg="cyan", bold=True)
            user_output(f"PR #{pr_number} already checked out at {styled_path}")
            user_output("\nShell integration not detected. Run 'erk init --shell' to set up.")
            user_output(f"Or use: source <(erk pr checkout {pr_reference} --script)")
        return

    # For cross-repository PRs, always fetch via refs/pull/<n>/head
    # For same-repo PRs, check if branch exists locally first
    if pr.is_cross_repository:
        # Fetch PR ref directly
        ctx.git.fetch_pr_ref(repo.root, "origin", pr_number, branch_name)
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
                ctx.git.fetch_pr_ref(repo.root, "origin", pr_number, branch_name)

    # Create worktree
    worktree_path = worktree_path_for(repo.worktrees_dir, branch_name)
    ctx.git.add_worktree(
        repo.root,
        worktree_path,
        branch=branch_name,
        ref=None,
        create_branch=False,
    )

    # Output based on mode
    if script:
        activation_script = render_activation_script(
            worktree_path=worktree_path,
            final_message=f'echo "Checked out PR #{pr_number} at $(pwd)"',
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name="pr-checkout",
            comment=f"activate PR #{pr_number}",
        )
        result.output_for_shell_integration()
    else:
        styled_path = click.style(str(worktree_path), fg="cyan", bold=True)
        user_output(f"Created worktree for PR #{pr_number} at {styled_path}")
        user_output("\nShell integration not detected. Run 'erk init --shell' to set up.")
        user_output(f"Or use: source <(erk pr checkout {pr_reference} --script)")
