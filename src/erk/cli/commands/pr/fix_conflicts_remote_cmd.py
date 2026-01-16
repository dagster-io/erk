"""Remote rebase with conflict resolution workflow.

Triggers a GitHub Actions workflow to:
1. Optionally squash commits on the branch
2. Rebase onto the PR's base branch
3. Use Claude to resolve any merge conflicts
4. Force push the rebased branch
"""

import click

from erk.cli.constants import REBASE_WORKFLOW_NAME
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


@click.command("fix-conflicts-remote")
@click.argument("pr_number", type=int, required=False)
@click.option(
    "--no-squash",
    is_flag=True,
    help="Skip squashing commits before rebase.",
)
@click.option(
    "--model",
    "model_name",
    type=str,
    help="Claude model for conflict resolution (default: claude-sonnet-4-5).",
)
@click.pass_obj
def pr_fix_conflicts_remote(
    ctx: ErkContext,
    pr_number: int | None,
    *,
    no_squash: bool,
    model_name: str | None,
) -> None:
    """Trigger remote rebase with AI-powered conflict resolution.

    This command triggers a GitHub Actions workflow that:

    \b
    1. Squashes all commits on the branch (unless --no-squash)
    2. Rebases onto the PR's base branch
    3. Uses Claude to resolve any merge conflicts
    4. Force pushes the rebased branch

    This is useful when your PR has merge conflicts and you want to resolve
    them remotely without switching to the branch locally.

    If PR_NUMBER is provided, triggers rebase for that PR (you don't need
    to be on the branch). Otherwise, uses the PR for the current branch.

    Examples:

    \b
        # Basic usage - squash and rebase current branch's PR
        erk pr fix-conflicts-remote

    \b
        # Trigger rebase for a specific PR (without checking out)
        erk pr fix-conflicts-remote 123

    \b
        # Rebase without squashing
        erk pr fix-conflicts-remote --no-squash

    \b
        # Use a specific model
        erk pr fix-conflicts-remote --model claude-sonnet-4-5

    Requirements:

    \b
    - Either be on a branch with an open PR, or provide a PR number
    - GitHub Actions secrets must be configured (ERK_QUEUE_GH_PAT, Claude credentials)
    """
    # Validate preconditions
    Ensure.gh_authenticated(ctx)
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)  # Type narrowing for ty
    repo: RepoContext = ctx.repo

    # Get PR details - either from explicit PR number or current branch
    user_output("Checking PR status...")
    if pr_number is not None:
        # Direct PR lookup by number
        pr = ctx.github.get_pr(repo.root, pr_number)
        Ensure.invariant(
            not isinstance(pr, PRNotFound),
            f"No pull request found with number #{pr_number}",
        )
        # Type narrowing after invariant check
        assert not isinstance(pr, PRNotFound)
        branch_name = pr.head_ref_name
    else:
        # Get PR from current branch (original behavior)
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd),
            "Not on a branch - checkout a branch or provide a PR number",
        )

        pr = ctx.github.get_pr_for_branch(repo.root, current_branch)
        Ensure.invariant(
            not isinstance(pr, PRNotFound),
            f"No pull request found for branch '{current_branch}'",
        )
        # Type narrowing after invariant check
        assert not isinstance(pr, PRNotFound)
        branch_name = current_branch

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot rebase {pr.state} PR - only OPEN PRs can be rebased",
    )

    resolved_pr_number = pr.number
    base_branch = pr.base_ref_name

    user_output(f"PR #{resolved_pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output(f"Base branch: {base_branch}")
    user_output("")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "branch_name": branch_name,
        "base_branch": base_branch,
        "pr_number": str(resolved_pr_number),
        "squash": "false" if no_squash else "true",
    }
    if model_name is not None:
        inputs["model_name"] = model_name

    # Trigger workflow
    user_output("Triggering rebase workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=REBASE_WORKFLOW_NAME,
        inputs=inputs,
    )
    user_output(click.style("✓", fg="green") + " Workflow triggered")
    user_output("")

    # Build run URL
    # Get owner/repo from the PR details
    run_url = f"https://github.com/{pr.owner}/{pr.repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")
