"""Pooled land command - merge current branch's PR without cleanup.

A simpler, safer alternative to `erk land` for pooled workflows:
- Merges the current branch's PR via squash merge
- Offers objective update (same as `erk land`)
- Does NOT delete the worktree or clean up the branch
"""

import click

from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    prompt_objective_update,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.github.types import PRDetails, PRNotFound
from erk_shared.output.output import user_output


@click.command("land")
@click.option("-f", "--force", is_flag=True, help="Skip objective update prompt")
@click.pass_obj
def pooled_land(ctx: ErkContext, force: bool) -> None:
    """Land current branch's PR via squash merge.

    This is a simpler alternative to `erk land` for pooled workflows:
    - Merges the PR with squash merge
    - Does NOT delete the worktree or branch
    - Offers to update linked objective (skipped with --force)

    Examples:
        erk pooled land           # Merge current branch's PR
        erk pooled land --force   # Merge and skip objective prompt
    """
    # Validate prerequisites
    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output("Error: Not currently on a branch (detached HEAD).")
        raise SystemExit(1)

    # Look up PR for current branch
    pr_result = ctx.github.get_pr_for_branch(main_repo_root, current_branch)

    if isinstance(pr_result, PRNotFound):
        user_output(
            f"Error: No pull request found for branch '{current_branch}'.\n"
            "Create a PR first with 'gh pr create' or 'gt submit'."
        )
        raise SystemExit(1)

    pr_details: PRDetails = pr_result
    pr_number = pr_details.number

    # Validate PR is OPEN
    if pr_details.state != "OPEN":
        user_output(f"Error: Pull request #{pr_number} is not open (state: {pr_details.state}).")
        raise SystemExit(1)

    # Merge the PR
    user_output(f"Merging PR #{pr_number}...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body if pr_details.body else None
    merge_result = ctx.github.merge_pr(main_repo_root, pr_number, subject=subject, body=body)

    if merge_result is not True:
        error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
        user_output(f"Error: Failed to merge PR #{pr_number}\n\n{error_detail}")
        raise SystemExit(1)

    user_output(click.style("✓", fg="green") + f" Merged PR #{pr_number} [{current_branch}]")

    # Check for linked objective and offer to update
    objective_number = get_objective_for_branch(ctx, main_repo_root, current_branch)
    if objective_number is not None:
        prompt_objective_update(
            ctx, main_repo_root, objective_number, pr_number, current_branch, force
        )

    # No cleanup - branch and worktree are preserved
    user_output("")
    user_output(
        click.style("Note: ", fg="cyan")
        + "Branch and worktree preserved. Use 'erk pooled unassign' to release the slot."
    )
