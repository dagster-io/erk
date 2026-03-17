"""Command to close a plan."""

import click

from erk.cli.commands.objective_helpers import run_objective_update_after_close
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option
from erk.core.context import ErkContext
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound


@click.command("close")
@click.argument("identifier", type=str)
@resolved_repo_option
@click.pass_obj
def pr_close(ctx: ErkContext, identifier: str, *, repo_id: GitHubRepoId) -> None:
    """Close a PR by PR number or GitHub URL.

    Closes all OPEN PRs linked to the issue in addition to closing the issue itself.

    Examples:
        erk pr close 42
        erk pr close 42 --repo owner/repo
    """
    remote = get_remote_github(ctx)

    number = parse_issue_identifier(identifier)

    # Verify plan exists
    issue = remote.get_issue(owner=repo_id.owner, repo=repo_id.repo, number=number)
    if isinstance(issue, IssueNotFound):
        raise click.ClickException(f"PR #{number} not found")

    # Close the plan + optional local enrichments
    objective_id: int | None = None
    if not isinstance(ctx.repo, NoRepoSentinel):
        repo_root = ctx.repo.root
        result = ctx.plan_store.get_managed_pr(repo_root, str(number))
        if not isinstance(result, PlanNotFound):
            objective_id = result.objective_id
        ctx.plan_store.close_managed_pr(repo_root, identifier)
    else:
        remote.close_issue(owner=repo_id.owner, repo=repo_id.repo, number=number)

    # Objective update (local only)
    if objective_id is not None:
        run_objective_update_after_close(
            ctx,
            pr_number=number,
            objective=objective_id,
        )

    # Output
    user_output(f"Closed PR #{number}")
