"""Remote PR review comment addressing workflow.

Triggers a GitHub Actions workflow to:
1. Checkout the PR branch
2. Use Claude to address PR review comments
3. Push any changes
"""

import click

from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata
from erk.cli.constants import PR_ADDRESS_WORKFLOW_NAME
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk_shared.github.types import PRNotFound
from erk_shared.output.output import user_output


@click.command("address-remote")
@click.argument("pr_number", type=int, required=True)
@click.option(
    "--model",
    "model_name",
    type=str,
    help="Claude model for addressing comments (default: claude-sonnet-4-5).",
)
@click.pass_obj
def pr_address_remote(
    ctx: ErkContext,
    pr_number: int,
    *,
    model_name: str | None,
) -> None:
    """Trigger remote PR review comment addressing.

    This command triggers a GitHub Actions workflow that:

    \b
    1. Checks out the PR branch
    2. Uses Claude to address PR review comments
    3. Pushes any changes made

    This is useful when you want to address PR review comments remotely
    without switching to the branch locally.

    PR_NUMBER is required - specify which PR to address.

    Examples:

    \b
        # Address review comments on PR #123
        erk pr address-remote 123

    \b
        # Use a specific model
        erk pr address-remote 123 --model claude-opus-4

    Requirements:

    \b
    - The specified PR must exist and be open
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

    # Get PR details by number
    user_output("Checking PR status...")
    pr = ctx.github.get_pr(repo.root, pr_number)
    Ensure.invariant(
        not isinstance(pr, PRNotFound),
        f"No pull request found with number #{pr_number}",
    )
    # Type narrowing after invariant check
    assert not isinstance(pr, PRNotFound)
    branch_name = pr.head_ref_name

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot address comments on {pr.state} PR - only OPEN PRs can be addressed",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output("")

    # Build workflow inputs
    inputs: dict[str, str] = {
        "pr_number": str(pr_number),
    }
    if model_name is not None:
        inputs["model_name"] = model_name

    # Trigger workflow
    user_output("Triggering pr-address workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=PR_ADDRESS_WORKFLOW_NAME,
        inputs=inputs,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow triggered")

    maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)

    user_output("")

    # Build run URL
    run_url = f"https://github.com/{pr.owner}/{pr.repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")
