"""Close a GitHub issue with a comment using REST API (avoids GraphQL rate limits).

Usage:
    erk exec close-issue-with-comment <ISSUE_NUMBER> --comment "Closing because..."

Output:
    JSON with {success, issue_number, comment_id}

Exit Codes:
    0: Success - issue closed with comment
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
from erk_shared.gateway.github.issues.types import CommentAddError, IssueCloseError


@click.command(name="close-issue-with-comment")
@click.argument("issue_number", type=int)
@click.option(
    "--comment",
    required=True,
    help="Comment body to add before closing",
)
@click.pass_context
def close_issue_with_comment(
    ctx: click.Context,
    issue_number: int,
    *,
    comment: str,
) -> None:
    """Close a GitHub issue with a comment using REST API."""
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Add the comment first
    comment_id = github.add_comment(repo_root, issue_number, comment)
    if isinstance(comment_id, CommentAddError):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": (
                        f"Failed to add comment to issue #{issue_number}: "
                        f"{comment_id.message}"
                    ),
                }
            )
        )
        raise SystemExit(1) from None

    # Then close the issue
    close_result = github.close_issue(repo_root, issue_number)
    if isinstance(close_result, IssueCloseError):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to close issue #{issue_number}: {close_result.message}",
                    "comment_id": comment_id,
                }
            )
        )
        raise SystemExit(1) from None

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "comment_id": comment_id,
            }
        )
    )
