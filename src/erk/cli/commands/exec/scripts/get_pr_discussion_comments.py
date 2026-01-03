"""Fetch PR discussion comments (main conversation thread) for agent context injection.

This exec command fetches discussion comments from the PR's main conversation
(not inline code review comments) and outputs them as JSON for agent processing.

Usage:
    erk exec get-pr-discussion-comments
    erk exec get-pr-discussion-comments --pr 123

Output:
    JSON with success status, PR info, and discussion comments

Exit Codes:
    0: Success (or graceful error with JSON output)
    1: Context not initialized

Examples:
    $ erk exec get-pr-discussion-comments
    {"success": true, "pr_number": 123, "comments": [...]}

    $ erk exec get-pr-discussion-comments --pr 456
    {"success": true, "pr_number": 456, "comments": [...]}
"""

import json
from typing import TypedDict

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
from erk_shared.github.issues.types import IssueComment
from erk_shared.github.types import PRDetails
from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    NoPRForBranch,
    PRNotFoundError,
)


def _ensure_branch(branch_result: str | BranchDetectionFailed) -> str:
    """Ensure branch was detected, exit with error if not."""
    if isinstance(branch_result, BranchDetectionFailed):
        exit_with_error(branch_result.error_type, branch_result.message)
    assert not isinstance(branch_result, BranchDetectionFailed)  # Type narrowing after NoReturn
    return branch_result


def _ensure_pr_result_for_branch(
    pr_result: PRDetails | NoPRForBranch,
) -> PRDetails:
    """Ensure PR lookup by branch succeeded, exit with appropriate error if not."""
    if isinstance(pr_result, NoPRForBranch):
        exit_with_error(pr_result.error_type, pr_result.message)
    assert not isinstance(pr_result, NoPRForBranch)  # Type narrowing after NoReturn
    return pr_result


def _ensure_pr_result_by_number(
    pr_result: PRDetails | PRNotFoundError,
) -> PRDetails:
    """Ensure PR lookup by number succeeded, exit with appropriate error if not."""
    if isinstance(pr_result, PRNotFoundError):
        exit_with_error(pr_result.error_type, pr_result.message)
    assert not isinstance(pr_result, PRNotFoundError)  # Type narrowing after NoReturn
    return pr_result


def _ensure_comments(
    comments_result: list[IssueComment] | GitHubAPIFailed,
) -> list[IssueComment]:
    """Ensure comments fetch succeeded, exit with error if not."""
    if isinstance(comments_result, GitHubAPIFailed):
        exit_with_error(comments_result.error_type, comments_result.message)
    assert not isinstance(comments_result, GitHubAPIFailed)  # Type narrowing after NoReturn
    return comments_result


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
        branch = _ensure_branch(GitHubChecks.branch(get_current_branch(ctx)))
        pr_details = _ensure_pr_result_for_branch(
            GitHubChecks.pr_for_branch(github, repo_root, branch)
        )
    else:
        pr_details = _ensure_pr_result_by_number(GitHubChecks.pr_by_number(github, repo_root, pr))

    # Fetch discussion comments (exits on failure)
    comments = _ensure_comments(
        GitHubChecks.issue_comments(github_issues, repo_root, pr_details.number)
    )

    # Format comments for JSON output
    formatted_comments: list[DiscussionCommentDict] = []
    for comment in comments:
        assert isinstance(comment, IssueComment)  # Runtime verification for type safety
        formatted_comments.append(
            {
                "id": comment.id,
                "author": comment.author,
                "body": comment.body,
                "url": comment.url,
            }
        )

    result = {
        "success": True,
        "pr_number": pr_details.number,
        "pr_url": pr_details.url,
        "pr_title": pr_details.title,
        "comments": formatted_comments,
    }
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)
