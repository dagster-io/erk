"""Update an issue's body using REST API (avoids GraphQL rate limits).

Usage:
    erk exec update-issue-body <ISSUE_NUMBER> --body "new body content"

Output:
    JSON with {success, issue_number, url}

Exit Codes:
    0: Success - issue updated
    1: Error - issue not found or API error
"""

import json

import click

from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)


@click.command(name="update-issue-body")
@click.argument("issue_number", type=int)
@click.option("--body", required=True, help="New body content")
@click.pass_context
def update_issue_body(
    ctx: click.Context,
    issue_number: int,
    *,
    body: str,
) -> None:
    """Update an issue's body using REST API (avoids GraphQL rate limits)."""
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # First get the issue to verify it exists and get URL
    try:
        issue = github.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to get issue #{issue_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Update the issue body
    try:
        github.update_issue_body(repo_root, issue_number, body)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to update issue #{issue_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "url": issue.url,
            }
        )
    )
