"""Update an issue's body using REST API (avoids GraphQL rate limits).

Usage:
    erk exec update-issue-body <ISSUE_NUMBER> --body "new body content"
    erk exec update-issue-body <ISSUE_NUMBER> --body-file /path/to/body.md

For large content (plans, objective roadmaps), prefer --body-file to avoid
shell quoting issues and argument length limits. Note: --body-stdin does not
exist - write content to a temp file and use --body-file instead.

Output:
    JSON with {success, issue_number, url}

Exit Codes:
    0: Success - issue updated
    1: Error - issue not found or API error
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)
from erk_shared.gateway.github.types import BodyFile, BodyText


@click.command(name="update-issue-body")
@click.argument("issue_number", type=int)
@click.option("--body", help="New body content")
@click.option(
    "--body-file",
    type=click.Path(exists=True, path_type=Path),
    help="Read body from file",
)
@click.pass_context
def update_issue_body(
    ctx: click.Context,
    issue_number: int,
    *,
    body: str | None,
    body_file: Path | None,
) -> None:
    """Update an issue's body using REST API (avoids GraphQL rate limits)."""
    # Mutual exclusivity validation
    if body is not None and body_file is not None:
        click.echo(
            json.dumps({"success": False, "error": "Cannot specify both --body and --body-file"})
        )
        raise SystemExit(1) from None

    if body is None and body_file is None:
        click.echo(json.dumps({"success": False, "error": "Must specify --body or --body-file"}))
        raise SystemExit(1) from None

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

    # Update the issue body - create appropriate wrapper type
    # Gateway handles file reading via gh api's -F body=@{path} syntax
    # At this point exactly one of body or body_file is set (validated above)
    if body_file is not None:
        body_arg = BodyFile(path=body_file)
    else:
        assert body is not None
        body_arg = BodyText(content=body)
    try:
        github.update_issue_body(repo_root, issue_number, body_arg)
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
