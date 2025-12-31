"""Add a reaction to a PR/issue comment to mark it as addressed.

This exec command adds a reaction (typically +1) to a PR discussion comment
to indicate the comment has been addressed.

Usage:
    erk exec add-reaction-to-comment --comment-id 12345
    erk exec add-reaction-to-comment --comment-id 12345 --reaction "+1"
    erk exec add-reaction-to-comment --comment-id 12345 --reaction "eyes"

Output:
    JSON with success status

Exit Codes:
    0: Always (even on error, to support || true pattern)
    1: Context not initialized

Examples:
    $ erk exec add-reaction-to-comment --comment-id 12345
    {"success": true, "comment_id": 12345, "reaction": "+1"}

    $ erk exec add-reaction-to-comment --comment-id 12345 --reaction "rocket"
    {"success": true, "comment_id": 12345, "reaction": "rocket"}
"""

import json

import click

from erk.cli.script_output import exit_with_error
from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.github.checks import GitHubChecks
from erk_shared.non_ideal_state import GitHubAPIFailed


@click.command(name="add-reaction-to-comment")
@click.option("--comment-id", required=True, type=int, help="Numeric comment ID")
@click.option(
    "--reaction",
    default="+1",
    help="Reaction type: +1, -1, laugh, confused, heart, hooray, rocket, eyes",
)
@click.pass_context
def add_reaction_to_comment(ctx: click.Context, comment_id: int, reaction: str) -> None:
    """Add a reaction to a PR/issue comment.

    Takes a numeric comment ID (from get-pr-discussion-comments output) and
    adds a reaction to mark the comment as addressed. Default reaction is +1.

    The GitHub API is idempotent - adding the same reaction twice returns
    the existing reaction.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github_issues = require_github_issues(ctx)

    # Add the reaction (exits on failure)
    reaction_result = GitHubChecks.add_reaction(github_issues, repo_root, comment_id, reaction)
    if isinstance(reaction_result, GitHubAPIFailed):
        exit_with_error(reaction_result.error_type, reaction_result.message)

    result = {
        "success": True,
        "comment_id": comment_id,
        "reaction": reaction,
    }
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)
