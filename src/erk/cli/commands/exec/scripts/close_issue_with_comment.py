"""Close an issue with a comment using REST API (avoids GraphQL rate limits).

Usage:
    erk exec close-issue-with-comment <ISSUE_NUMBER> --comment "message"

Output:
    JSON with {success, issue_number, comment_id}

Exit Codes:
    0: Success - issue closed with comment
    1: Error - issue not found or API error
"""

import json

import click

from erk_shared.context.helpers import require_issues, require_repo_root


@click.command(name="close-issue-with-comment")
@click.argument("issue_number", type=int)
@click.option("--comment", required=True, help="Comment to add before closing")
@click.pass_context
def close_issue_with_comment(
    ctx: click.Context,
    issue_number: int,
    *,
    comment: str,
) -> None:
    """Close an issue with a comment."""
    github_issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # First add the comment
    try:
        comment_id = github_issues.add_comment(repo_root, issue_number, comment)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to add comment to issue #{issue_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Then close the issue
    try:
        github_issues.close_issue(repo_root, issue_number)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to close issue #{issue_number}: {e}",
                    "comment_id": comment_id,
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "comment_id": comment_id,
            }
        )
    )
