"""Fetch all PR feedback (review threads + discussion comments) in a single command.

Combines the functionality of get-pr-review-comments and get-pr-discussion-comments
into one command, eliminating redundant PR lookups and enabling parallel fetches.

Usage:
    erk exec get-pr-feedback
    erk exec get-pr-feedback --pr 123
    erk exec get-pr-feedback --include-resolved

Output:
    JSON with pr_info, review_threads, and discussion_comments sections

Exit Codes:
    0: Success (or graceful error with JSON output)
    1: Context not initialized
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict

import click

from erk.cli.script_output import exit_with_error, handle_non_ideal_exit
from erk_shared.context.helpers import (
    get_current_branch,
    require_github,
    require_issues,
    require_repo_root,
)
from erk_shared.gateway.github.checks import GitHubChecks
from erk_shared.gateway.github.issues.types import IssueComment
from erk_shared.gateway.github.types import PRReviewThread
from erk_shared.non_ideal_state import BranchDetectionFailed

# --- JSON output types ---


class ReviewCommentDict(TypedDict):
    author: str
    body: str
    created_at: str


class ReviewThreadDict(TypedDict):
    id: str
    path: str
    line: int | None
    is_outdated: bool
    comments: list[ReviewCommentDict]


class DiscussionCommentDict(TypedDict):
    id: int
    author: str
    body: str
    url: str


# --- Formatting helpers ---


def _format_thread(thread: PRReviewThread) -> ReviewThreadDict:
    """Format a PRReviewThread for JSON output."""
    comments: list[ReviewCommentDict] = []
    for comment in thread.comments:
        comments.append(
            {
                "author": comment.author,
                "body": comment.body,
                "created_at": comment.created_at,
            }
        )
    return {
        "id": thread.id,
        "path": thread.path,
        "line": thread.line,
        "is_outdated": thread.is_outdated,
        "comments": comments,
    }


def _format_discussion_comment(comment: IssueComment) -> DiscussionCommentDict:
    """Format an IssueComment for JSON output."""
    return {
        "id": comment.id,
        "author": comment.author,
        "body": comment.body,
        "url": comment.url,
    }


# --- Command ---


@click.command(name="get-pr-feedback")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.option("--include-resolved", is_flag=True, help="Include resolved review threads")
@click.pass_context
@handle_non_ideal_exit
def get_pr_feedback(ctx: click.Context, pr: int | None, include_resolved: bool) -> None:
    """Fetch all PR feedback in a single command.

    Combines review threads (GraphQL) and discussion comments (REST) into
    one JSON response. Fetches both in parallel after a single PR lookup.

    If --pr is not specified, finds the PR for the current branch.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)

    # Single PR lookup
    if pr is None:
        branch = GitHubChecks.branch(get_current_branch(ctx))
        if isinstance(branch, BranchDetectionFailed):
            branch.ensure()
        assert not isinstance(branch, BranchDetectionFailed)  # Type narrowing after NoReturn
        pr_details = GitHubChecks.pr_for_branch(github, repo_root, branch).ensure()
    else:
        pr_details = GitHubChecks.pr_by_number(github, repo_root, pr).ensure()

    # Parallel fetch of review threads and discussion comments
    with ThreadPoolExecutor(max_workers=2) as executor:
        threads_future = executor.submit(
            github.get_pr_review_threads,
            repo_root,
            pr_details.number,
            include_resolved=include_resolved,
        )
        comments_future = executor.submit(
            GitHubChecks.issue_comments,
            github_issues,
            repo_root,
            pr_details.number,
        )

        try:
            threads = threads_future.result()
        except RuntimeError as e:
            exit_with_error("github-api-failed", str(e))

        comments = comments_future.result().ensure()

    # Filter out threads with invalid IDs
    valid_threads = [t for t in threads if t.id]

    result = {
        "success": True,
        "pr_number": pr_details.number,
        "pr_url": pr_details.url,
        "pr_title": pr_details.title,
        "review_threads": [_format_thread(t) for t in valid_threads],
        "discussion_comments": [_format_discussion_comment(c) for c in comments],
    }
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)
