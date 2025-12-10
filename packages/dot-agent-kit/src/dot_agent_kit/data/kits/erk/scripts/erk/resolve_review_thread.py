"""Resolve a PR review thread via GraphQL mutation.

This kit CLI command resolves a single PR review thread and outputs
JSON with the result. Optionally adds a reply comment before resolving.

Usage:
    erk kit exec erk resolve-review-thread --thread-id "PRRT_xxxx"
    erk kit exec erk resolve-review-thread --thread-id "PRRT_xxxx" --comment "Resolved via ..."

Output:
    JSON with success status

Exit Codes:
    0: Always (even on error, to support || true pattern)
    1: Context not initialized

Examples:
    $ erk kit exec erk resolve-review-thread --thread-id "PRRT_abc123"
    {"success": true, "thread_id": "PRRT_abc123"}

    $ erk kit exec erk resolve-review-thread --thread-id "PRRT_abc123" --comment "Fixed"
    {"success": true, "thread_id": "PRRT_abc123", "comment_added": true}

    $ erk kit exec erk resolve-review-thread --thread-id "invalid"
    {"success": false, "error_type": "resolution_failed", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import click
from erk_shared.context.helpers import require_github, require_repo_root

if TYPE_CHECKING:
    from erk_shared.github.abc import GitHub

T = TypeVar("T")


@dataclass(frozen=True)
class ResolveThreadSuccess:
    """Success response for thread resolution."""

    success: bool
    thread_id: str
    comment_added: bool = False


@dataclass(frozen=True)
class ResolveThreadError:
    """Error response for thread resolution."""

    success: bool
    error_type: str
    message: str


def _format_resolution_comment(comment: str) -> str:
    """Format a resolution comment with timestamp and source attribution.

    Args:
        comment: The user-provided comment text

    Returns:
        Formatted comment with timestamp and /erk:pr-address attribution
    """
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f"{comment}\n\n_Addressed via `/erk:pr-address` at {timestamp}_"


def _ensure_not_error(result: T | ResolveThreadError) -> T:
    """Ensure result is not an error, otherwise output JSON and exit.

    Provides type narrowing: takes `T | ResolveThreadError` and returns `T`.

    Args:
        result: Value that may be a ResolveThreadError

    Returns:
        The value unchanged if not an error (with narrowed type T)

    Raises:
        SystemExit: If result is ResolveThreadError (with exit code 0)
    """
    if isinstance(result, ResolveThreadError):
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)
    return result


def _add_comment_if_provided(
    github: "GitHub",
    repo_root: Path,
    thread_id: str,
    comment: str | None,
) -> bool | ResolveThreadError:
    """Add a comment to the thread if provided.

    Returns:
        True/False for comment_added status, or ResolveThreadError on failure
    """
    if comment is None:
        return False

    formatted_comment = _format_resolution_comment(comment)
    try:
        return github.add_review_thread_reply(repo_root, thread_id, formatted_comment)
    except RuntimeError as e:
        return ResolveThreadError(
            success=False,
            error_type="comment_failed",
            message=f"Failed to add comment: {e}",
        )


@click.command(name="resolve-review-thread")
@click.option("--thread-id", required=True, help="GraphQL node ID of the thread to resolve")
@click.option("--comment", default=None, help="Optional comment to add before resolving")
@click.pass_context
def resolve_review_thread(ctx: click.Context, thread_id: str, comment: str | None) -> None:
    """Resolve a PR review thread.

    Takes a GraphQL node ID (from get-pr-review-comments output) and
    marks the thread as resolved. Optionally adds a reply comment first.

    THREAD_ID: GraphQL node ID of the review thread
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Add comment first if provided
    comment_added = _ensure_not_error(
        _add_comment_if_provided(github, repo_root, thread_id, comment)
    )

    # Attempt to resolve the thread
    try:
        resolved = github.resolve_review_thread(repo_root, thread_id)
    except RuntimeError as e:
        result = ResolveThreadError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    if resolved:
        result_success = ResolveThreadSuccess(
            success=True,
            thread_id=thread_id,
            comment_added=comment_added,
        )
        click.echo(json.dumps(asdict(result_success), indent=2))
    else:
        result_error = ResolveThreadError(
            success=False,
            error_type="resolution_failed",
            message=f"Failed to resolve thread {thread_id}",
        )
        click.echo(json.dumps(asdict(result_error), indent=2))

    raise SystemExit(0)
