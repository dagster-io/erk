"""Fetch PR review comments for agent context injection.

This kit CLI command fetches unresolved (or all) PR review comments from GitHub
and outputs them as JSON for agent processing.

Usage:
    dot-agent run erk get-pr-review-comments
    dot-agent run erk get-pr-review-comments --pr 123
    dot-agent run erk get-pr-review-comments --include-resolved

Output:
    JSON with success status, PR info, and review threads

Exit Codes:
    0: Success (or graceful error with JSON output)
    1: Context not initialized

Examples:
    $ dot-agent run erk get-pr-review-comments
    {"success": true, "pr_number": 123, "threads": [...]}

    $ dot-agent run erk get-pr-review-comments --pr 456
    {"success": true, "pr_number": 456, "threads": [...]}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import NoReturn, TypedDict

import click
from erk_shared.github.types import PRDetails, PRNotFound, PRReviewThread

from dot_agent_kit.context_helpers import (
    get_current_branch,
    require_github,
    require_repo_root,
)


class ReviewCommentDict(TypedDict):
    """Typed dict for a single review comment in JSON output."""

    author: str
    body: str
    created_at: str


class ReviewThreadDict(TypedDict):
    """Typed dict for a review thread in JSON output."""

    id: str
    path: str
    line: int | None
    is_outdated: bool
    comments: list[ReviewCommentDict]


@dataclass(frozen=True)
class ReviewCommentSuccess:
    """Success response for PR review comments."""

    success: bool
    pr_number: int
    pr_url: str
    pr_title: str
    threads: list[ReviewThreadDict]


@dataclass(frozen=True)
class ReviewCommentError:
    """Error response for PR review comments."""

    success: bool
    error_type: str
    message: str


def _exit_with_error(error_type: str, message: str) -> NoReturn:
    """Output JSON error and exit with success code."""
    result = ReviewCommentError(success=False, error_type=error_type, message=message)
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


def _ensure_branch(branch: str | None) -> str:
    """Ensure branch was detected, exit with error if not."""
    if branch is None:
        _exit_with_error("branch_detection_failed", "Could not determine current branch")
    return branch


def _ensure_pr_result(
    pr_result: PRDetails | PRNotFound,
    *,
    branch: str | None = None,
    pr_number: int | None = None,
) -> PRDetails:
    """Ensure PR lookup succeeded, exit with appropriate error if not."""
    if isinstance(pr_result, PRNotFound):
        if branch is not None:
            _exit_with_error("no_pr_for_branch", f"No PR found for branch '{branch}'")
        else:
            _exit_with_error("pr_not_found", f"PR #{pr_number} not found")
    return pr_result


def _format_thread_for_json(thread: PRReviewThread) -> ReviewThreadDict:
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


@click.command(name="get-pr-review-comments")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.option("--include-resolved", is_flag=True, help="Include resolved threads")
@click.pass_context
def get_pr_review_comments(ctx: click.Context, pr: int | None, include_resolved: bool) -> None:
    """Fetch PR review comments for agent context injection.

    Queries GitHub for review threads on a pull request and outputs
    structured JSON for agent processing. By default, excludes resolved
    threads.

    If --pr is not specified, finds the PR for the current branch.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Get PR details - either from current branch or specified PR number
    if pr is None:
        branch = _ensure_branch(get_current_branch(ctx))
        pr_result = _ensure_pr_result(github.get_pr_for_branch(repo_root, branch), branch=branch)
    else:
        pr_result = _ensure_pr_result(github.get_pr(repo_root, pr), pr_number=pr)

    # Fetch review threads
    try:
        threads = github.get_pr_review_threads(
            repo_root, pr_result.number, include_resolved=include_resolved
        )
    except RuntimeError as e:
        _exit_with_error("github_api_failed", str(e))

    result_success = ReviewCommentSuccess(
        success=True,
        pr_number=pr_result.number,
        pr_url=pr_result.url,
        pr_title=pr_result.title,
        threads=[_format_thread_for_json(t) for t in threads],
    )
    click.echo(json.dumps(asdict(result_success), indent=2))
    raise SystemExit(0)
