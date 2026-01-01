"""Post or update a PR summary comment with a unique marker.

This exec command finds an existing PR comment containing a marker,
updates it if found, or creates a new comment if not found.

Usage:
    erk exec post-or-update-pr-summary --pr-number 123 \\
        --marker "<!-- my-marker -->" --body "Summary text"

Output:
    JSON with success status, action taken (created/updated), and comment ID

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk exec post-or-update-pr-summary --pr-number 123 \\
        --marker "<!-- review -->" --body "# Review"
    {"success": true, "action": "created", "comment_id": 12345}

    $ erk exec post-or-update-pr-summary --pr-number 123 \\
        --marker "<!-- review -->" --body "# Updated"
    {"success": true, "action": "updated", "comment_id": 12345}
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_github, require_repo_root


@dataclass(frozen=True)
class SummaryCommentSuccess:
    """Success response for summary comment posting."""

    success: bool
    action: str  # "created" or "updated"
    comment_id: int


@dataclass(frozen=True)
class SummaryCommentError:
    """Error response for summary comment posting."""

    success: bool
    error_type: str
    message: str


@click.command(name="post-or-update-pr-summary")
@click.option("--pr-number", required=True, type=int, help="PR number to comment on")
@click.option("--marker", required=True, help="HTML marker to identify the comment")
@click.option("--body", required=True, help="Comment body text (must include marker)")
@click.pass_context
def post_or_update_pr_summary(
    ctx: click.Context,
    pr_number: int,
    marker: str,
    body: str,
) -> None:
    """Post or update a PR summary comment.

    Finds an existing comment containing the marker and updates it,
    or creates a new comment if none found. The body should include
    the marker for future lookups.

    PR_NUMBER: The PR to comment on
    MARKER: HTML marker to identify the comment (e.g., <!-- my-review -->)
    BODY: Comment text (should include the marker for future updates)
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Ensure body contains the marker for future lookups
    if marker not in body:
        result = SummaryCommentError(
            success=False,
            error_type="marker_not_in_body",
            message=f"The body must contain the marker '{marker}' for future lookups",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Try to find existing comment with marker
    try:
        existing_id = github.find_pr_comment_by_marker(repo_root, pr_number, marker)
    except RuntimeError as e:
        result = SummaryCommentError(
            success=False,
            error_type="find_failed",
            message=f"Failed to search for existing comment: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    if existing_id is not None:
        # Update existing comment
        try:
            github.update_pr_comment(repo_root, existing_id, body)
            result_success = SummaryCommentSuccess(
                success=True,
                action="updated",
                comment_id=existing_id,
            )
            click.echo(json.dumps(asdict(result_success), indent=2))
        except RuntimeError as e:
            result = SummaryCommentError(
                success=False,
                error_type="update_failed",
                message=str(e),
            )
            click.echo(json.dumps(asdict(result), indent=2))
    else:
        # Create new comment
        try:
            comment_id = github.create_pr_comment(repo_root, pr_number, body)
            result_success = SummaryCommentSuccess(
                success=True,
                action="created",
                comment_id=comment_id,
            )
            click.echo(json.dumps(asdict(result_success), indent=2))
        except RuntimeError as e:
            result = SummaryCommentError(
                success=False,
                error_type="create_failed",
                message=str(e),
            )
            click.echo(json.dumps(asdict(result), indent=2))

    raise SystemExit(0)
