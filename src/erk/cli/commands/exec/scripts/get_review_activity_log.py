"""Fetch the activity log from an existing review summary comment.

This exec command finds the PR comment containing the given marker
and extracts the Activity Log section from it.

Usage:
    erk exec get-review-activity-log --pr-number 123 \\
        --marker "<!-- audit-pr-docs -->"

Output:
    JSON with found status and activity log text

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk exec get-review-activity-log --pr-number 123 \\
        --marker "<!-- audit-pr-docs -->"
    {"success": true, "found": true, "activity_log": "- [2024-01-01] ..."}

    $ erk exec get-review-activity-log --pr-number 123 \\
        --marker "<!-- no-such-marker -->"
    {"success": true, "found": false, "activity_log": ""}
"""

import json

import click

from erk_shared.context.helpers import require_github, require_repo_root


def _extract_activity_log(body: str) -> str:
    """Extract everything after '### Activity Log' from a comment body.

    Returns empty string if the section is not found.
    """
    marker = "### Activity Log"
    idx = body.find(marker)
    if idx == -1:
        return ""
    # Skip past the heading line
    after_heading = body[idx + len(marker) :]
    # Strip leading whitespace/newlines after the heading
    return after_heading.strip()


@click.command(name="get-review-activity-log")
@click.option("--pr-number", required=True, type=int, help="PR number to search")
@click.option("--marker", required=True, help="HTML marker identifying the review comment")
@click.pass_context
def get_review_activity_log(
    ctx: click.Context,
    pr_number: int,
    marker: str,
) -> None:
    """Fetch the activity log from an existing review summary comment.

    Finds the PR comment containing MARKER and extracts the Activity Log
    section. Returns JSON with the extracted log text.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    comment_body = github.get_pr_comment_body_by_marker(repo_root, pr_number, marker)

    if comment_body is None:
        result = {"success": True, "found": False, "activity_log": ""}
        click.echo(json.dumps(result, indent=2))
        raise SystemExit(0)

    activity_log = _extract_activity_log(comment_body)
    result = {"success": True, "found": True, "activity_log": activity_log}
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)
