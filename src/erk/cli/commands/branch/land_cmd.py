"""Land a PR by branch name.

This command looks up the PR for a given branch and lands it.

Usage:
    erk br land <branch_name>
"""

import click

from erk.cli.commands.navigation_helpers import check_clean_working_tree
from erk.cli.commands.pr.land_cmd import _cleanup_and_navigate
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


@click.command("land", cls=CommandWithHiddenOptions)
@script_option
@click.argument("branch_name")
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
def br_land(
    ctx: ErkContext,
    script: bool,
    branch_name: str,
    force: bool,
    pull_flag: bool,
) -> None:
    """Land a PR by branch name.

    Looks up the PR for the specified branch and merges it.

    \b
    Usage:
      erk br land feature-123

    Requires:
    - Graphite enabled: 'erk config set use_graphite true'
    - Branch must have an open PR
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
            + "  1. Use shell integration: erk br land <branch>\n"
            + "     (Requires 'erk init --shell' setup)\n\n"
            + "  2. Use --script flag: source <(erk br land <branch> --script)\n"
        )
        raise SystemExit(1)

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
            + f"Then retry: erk br land {branch_name}"
        )
        raise SystemExit(1)

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

    # Cleanup and navigate (uses shared function from pr/land_cmd.py)
    _cleanup_and_navigate(
        ctx,
        repo,
        branch_name,
        worktree_path,
        script,
        pull_flag,
        force,
        is_current_branch,
        target_child_branch=None,
    )
