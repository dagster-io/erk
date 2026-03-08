"""Close an objective GitHub issue."""

import click

from erk.cli.alias import alias
from erk.cli.commands.pr.repo_resolution import get_remote_github, repo_option, resolve_owner_repo
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.output.output import user_output

ERK_OBJECTIVE_LABEL = "erk-objective"


@alias("c")
@click.command("close")
@click.argument("issue_ref")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@repo_option
@click.pass_obj
def close_objective(
    ctx: ErkContext,
    issue_ref: str,
    *,
    force: bool,
    target_repo: str | None,
) -> None:
    """Close an objective GitHub issue.

    ISSUE_REF can be an issue number (42), P-prefixed (P42), or a full GitHub URL.

    The issue must have the 'erk-objective' label and be in an open state.
    """
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)
    issue_number = parse_issue_identifier(issue_ref)

    # Fetch the issue
    issue = remote.get_issue(owner=owner, repo=repo_name, number=issue_number)
    if isinstance(issue, IssueNotFound):
        user_output(click.style("Error: ", fg="red") + f"Issue #{issue_number} not found")
        raise SystemExit(1)

    # Validate issue has erk-objective label
    if ERK_OBJECTIVE_LABEL not in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} is not an objective (missing '{ERK_OBJECTIVE_LABEL}' label)"
        )
        raise SystemExit(1)

    # Validate issue is open
    if issue.state.upper() != "OPEN":
        user_output(click.style("Error: ", fg="red") + f"Issue #{issue_number} is already closed")
        raise SystemExit(1)

    # Prompt for confirmation unless --force is provided
    if not force:
        if not ctx.console.confirm(
            f"Close objective #{issue_number} ({issue.title})?",
            default=True,
        ):
            user_output("Cancelled.")
            raise SystemExit(0)

    # Close the issue
    remote.close_issue(owner=owner, repo=repo_name, number=issue_number)

    user_output(click.style("✓ ", fg="green") + f"Closed objective #{issue_number}: {issue.url}")
