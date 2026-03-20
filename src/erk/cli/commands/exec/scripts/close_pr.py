"""Close a plan with a comment.

Usage:
    erk exec close-pr <PR_NUMBER> --comment "Closing because..."

Output:
    JSON with {success, pr_number, comment_id}

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


@click.command(name="close-pr")
@click.argument("pr_number", type=int)
@click.option(
    "--comment",
    required=True,
    help="Comment body to add before closing",
)
@click.pass_context
def close_pr(
    ctx: click.Context,
    pr_number: int,
    *,
    comment: str,
) -> None:
    """Close a plan with a comment."""
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    pr_id = str(pr_number)

    # Add the comment first
    try:
        comment_id = backend.add_comment(repo_root, pr_id, comment)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to add comment to PR #{pr_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Then close the plan
    try:
        backend.close_managed_pr(repo_root, pr_id)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to close PR #{pr_number}: {e}",
                    "comment_id": comment_id,
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "pr_number": pr_number,
                "comment_id": comment_id,
            }
        )
    )
