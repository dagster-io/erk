# type: ignore  # TODO: Fix ty errors in follow-up PR
"""Reply to a PR discussion comment with a blockquote and action summary.

This exec command posts a reply to a discussion comment that:
1. Quotes the original comment with author attribution
2. Includes an action summary explaining what was done
3. Adds a reaction to the original comment

Usage:
    erk exec reply-to-discussion-comment --comment-id 12345 --reply "Action taken: ..."
    erk exec reply-to-discussion-comment --comment-id 12345 --pr 789 --reply "..."

Output:
    JSON with success status and reply details

Exit Codes:
    0: Success
    1: Error (comment not found, API failure, etc.)

Examples:
    $ erk exec reply-to-discussion-comment --comment-id 12345 --reply "Fixed typo in docs"
    {"success": true, "comment_id": 12345, "reply_id": 67890}
"""

import json
from datetime import UTC, datetime

import click

from erk.cli.script_output import exit_with_error
from erk_shared.context.helpers import (
    get_current_branch,
    require_github,
    require_repo_root,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.github.checks import GitHubChecks
from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    NoPRForBranch,
    PRNotFoundError,
)


def _format_reply(author: str, url: str, body: str, action_summary: str) -> str:
    """Format a reply with blockquote of original comment and action summary.

    Args:
        author: Original comment author's GitHub login
        url: URL to the original comment
        body: Body of the original comment
        action_summary: Description of action taken

    Returns:
        Formatted markdown reply
    """
    # Quote the original comment (truncate if very long)
    quoted_lines = body.strip().split("\n")
    if len(quoted_lines) > 10:
        # Truncate long comments
        quoted_body = "\n".join(quoted_lines[:10]) + "\n> ..."
    else:
        quoted_body = body.strip()

    # Add blockquote prefix to each line
    quoted = "\n".join(f"> {line}" for line in quoted_body.split("\n"))

    # Get current timestamp
    now = datetime.now(UTC).strftime("%Y-%m-%d %I:%M %p UTC")

    return f"""> **@{author}** [commented]({url}):
{quoted}

{action_summary}

---
<sub>Addressed via `/erk:pr-address` at {now}</sub>"""


@click.command(name="reply-to-discussion-comment")
@click.option("--comment-id", required=True, type=int, help="Numeric comment ID to reply to")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.option("--reply", required=True, help="Action summary text (what was done)")
@click.pass_context
def reply_to_discussion_comment(
    ctx: click.Context, comment_id: int, pr: int | None, reply: str
) -> None:
    """Reply to a PR discussion comment with quote and action summary.

    Fetches the original comment to get its author and body, then posts a
    formatted reply quoting the original with your action summary. Also adds
    a +1 reaction to the original comment.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    github_issues = require_github_issues(ctx)

    # Get PR details - either from current branch or specified PR number
    if pr is None:
        branch_result = GitHubChecks.branch(get_current_branch(ctx))
        if isinstance(branch_result, BranchDetectionFailed):
            exit_with_error(branch_result.error_type, branch_result.message)
        branch = branch_result

        pr_result = GitHubChecks.pr_for_branch(github, repo_root, branch)
        if isinstance(pr_result, NoPRForBranch):
            exit_with_error(pr_result.error_type, pr_result.message)
        pr_details = pr_result
    else:
        pr_result = GitHubChecks.pr_by_number(github, repo_root, pr)
        if isinstance(pr_result, PRNotFoundError):
            exit_with_error(pr_result.error_type, pr_result.message)
        pr_details = pr_result

    # Fetch all discussion comments to find the one we're replying to
    comments_result = GitHubChecks.issue_comments(github_issues, repo_root, pr_details.number)
    if isinstance(comments_result, GitHubAPIFailed):
        exit_with_error(comments_result.error_type, comments_result.message)

    # Find the comment by ID
    target_comment = None
    for comment in comments_result:
        if comment.id == comment_id:
            target_comment = comment
            break

    if target_comment is None:
        exit_with_error(
            "comment_not_found",
            f"Comment ID {comment_id} not found in PR #{pr_details.number} discussion",
        )

    # Format the reply
    reply_body = _format_reply(
        author=target_comment.author,
        url=target_comment.url,
        body=target_comment.body,
        action_summary=reply,
    )

    # Post the reply as a new comment
    try:
        reply_comment_id = github_issues.add_comment(repo_root, pr_details.number, reply_body)
    except RuntimeError as e:
        exit_with_error("github_api_error", f"Failed to post reply: {e}")

    # Add reaction to original comment
    reaction_result = GitHubChecks.add_reaction(github_issues, repo_root, comment_id, "+1")
    if isinstance(reaction_result, GitHubAPIFailed):
        # Non-fatal: reply was posted, just log warning
        click.echo(
            f"Warning: Reply posted but failed to add reaction: {reaction_result.message}",
            err=True,
        )

    result = {
        "success": True,
        "comment_id": comment_id,
        "reply_id": reply_comment_id,
        "pr_number": pr_details.number,
    }
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)
