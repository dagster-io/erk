"""Fetch PR discussion comments (main conversation thread) for agent context injection.

This kit CLI command fetches discussion comments from the PR's main conversation
(not inline code review comments) and outputs them as JSON for agent processing.

Usage:
    erk kit exec erk get-pr-discussion-comments
    erk kit exec erk get-pr-discussion-comments --pr 123

Output:
    JSON with success status, PR info, and discussion comments

Exit Codes:
    0: Success (or graceful error with JSON output)
    1: Context not initialized

Examples:
    $ erk kit exec erk get-pr-discussion-comments
    {"success": true, "pr_number": 123, "comments": [...]}

    $ erk kit exec erk get-pr-discussion-comments --pr 456
    {"success": true, "pr_number": 456, "comments": [...]}
"""

import json
from typing import TypedDict

import click
from erk_shared.context.helpers import get_current_branch, require_github, require_repo_root

from dot_agent_kit.cli_result import exit_with_error
from dot_agent_kit.context_helpers import require_github_issues
from dot_agent_kit.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    GitHubChecks,
    NoPRForBranch,
    PRNotFoundError,
)


class DiscussionCommentDict(TypedDict):
    """Typed dict for a single discussion comment in JSON output."""

    id: int
    author: str
    body: str
    url: str


@click.command(name="get-pr-discussion-comments")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.pass_context
def get_pr_discussion_comments(ctx: click.Context, pr: int | None) -> None:
    """Fetch PR discussion comments for agent context injection.

    Queries GitHub for discussion comments on a pull request's main
    conversation thread (not inline code review comments) and outputs
    structured JSON for agent processing.

    If --pr is not specified, finds the PR for the current branch.
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

    # Fetch discussion comments (exits on failure)
    comments_result = GitHubChecks.issue_comments(github_issues, repo_root, pr_details.number)
    if isinstance(comments_result, GitHubAPIFailed):
        exit_with_error(comments_result.error_type, comments_result.message)
    comments = comments_result

    # Format comments for JSON output
    formatted_comments: list[DiscussionCommentDict] = [
        {
            "id": comment.id,
            "author": comment.author,
            "body": comment.body,
            "url": comment.url,
        }
        for comment in comments
    ]

    result = {
        "success": True,
        "pr_number": pr_details.number,
        "pr_url": pr_details.url,
        "pr_title": pr_details.title,
        "comments": formatted_comments,
    }
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)
