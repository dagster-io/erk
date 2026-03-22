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

from erk.cli.pr_ref_type import PR_REF
from erk_shared.context.helpers import (
    require_pr_backend,
    require_repo_root,
)


@click.command(name="close-pr")
@click.argument("pr", type=PR_REF)
@click.option(
    "--comment",
    required=True,
    help="Comment body to add before closing",
)
@click.pass_context
def close_pr(
    ctx: click.Context,
    pr: int,
    *,
    comment: str,
) -> None:
    """Close a plan with a comment."""
    backend = require_pr_backend(ctx)
    repo_root = require_repo_root(ctx)
    pr_id = str(pr)

    # Add the comment first
    try:
        comment_id = backend.add_comment(repo_root, pr_id, comment)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to add comment to PR #{pr}: {e}",
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
                    "error": f"Failed to close PR #{pr}: {e}",
                    "comment_id": comment_id,
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "pr_number": pr,
                "comment_id": comment_id,
            }
        )
    )
