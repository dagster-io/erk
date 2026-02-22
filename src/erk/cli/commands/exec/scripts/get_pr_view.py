"""Fetch PR details using REST API (avoids GraphQL rate limits).

Usage:
    erk exec get-pr-view [PR_NUMBER] [--branch BRANCH]

Output:
    JSON with PR metadata (number, title, body, state, labels, etc.)

Exit Codes:
    0: Success - PR fetched
    1: Error - PR not found or no branch detected
"""

import json

import click

from erk_shared.context.helpers import (
    get_current_branch,
    require_github,
    require_repo_root,
)
from erk_shared.gateway.github.types import PRNotFound


@click.command(name="get-pr-view")
@click.argument("pr_number", type=int, required=False, default=None)
@click.option("--branch", type=str, default=None, help="Branch name to look up PR for")
@click.pass_context
def get_pr_view(ctx: click.Context, *, pr_number: int | None, branch: str | None) -> None:
    """Fetch PR details using REST API (avoids GraphQL rate limits)."""
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    if pr_number is not None:
        result = github.get_pr(repo_root, pr_number)
    elif branch is not None:
        result = github.get_pr_for_branch(repo_root, branch)
    else:
        detected_branch = get_current_branch(ctx)
        if detected_branch is None:
            click.echo(json.dumps({"success": False, "error": "Could not detect current branch"}))
            raise SystemExit(1)
        result = github.get_pr_for_branch(repo_root, detected_branch)

    if isinstance(result, PRNotFound):
        click.echo(json.dumps({"success": False, "error": "PR not found"}))
        raise SystemExit(1)

    click.echo(
        json.dumps(
            {
                "success": True,
                "number": result.number,
                "title": result.title,
                "url": result.url,
                "body": result.body,
                "state": result.state,
                "is_draft": result.is_draft,
                "head_ref_name": result.head_ref_name,
                "base_ref_name": result.base_ref_name,
                "labels": list(result.labels),
                "author": result.author,
                "mergeable": result.mergeable,
                "merge_state_status": result.merge_state_status,
                "is_cross_repository": result.is_cross_repository,
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat(),
            }
        )
    )
