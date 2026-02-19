"""Close a plan with a comment.

Usage:
    erk exec close-issue-with-comment <ISSUE_NUMBER> --comment "Closing because..."

Output:
    JSON with {success, issue_number, comment_id}

Exit Codes:
    0: Success - plan closed with comment
    1: Error - plan not found or API error
"""

import json

import click

from erk_shared.context.helpers import (
    require_plan_backend,
    require_repo_root,
)


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
    """Close a plan with a comment."""
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    plan_id = str(issue_number)

    # Add the comment first
    try:
        comment_id = backend.add_comment(repo_root, plan_id, comment)
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

    # Then close the plan
    try:
        backend.close_plan(repo_root, plan_id)
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
