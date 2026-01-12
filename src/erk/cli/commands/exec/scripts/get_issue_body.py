"""Fetch an issue's body using REST API (avoids GraphQL rate limits).

Usage:
    erk exec get-issue-body <ISSUE_NUMBER>

Output:
    JSON with {success, issue_number, title, body, state, labels, url}

Exit Codes:
    0: Success - issue fetched
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


@click.command(name="get-issue-body")
@click.argument("issue_number", type=int)
@click.pass_context
def get_issue_body(ctx: click.Context, issue_number: int) -> None:
    """Fetch an issue's body using REST API (avoids GraphQL rate limits)."""
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

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

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "labels": issue.labels,
                "url": issue.url,
            }
        )
    )
