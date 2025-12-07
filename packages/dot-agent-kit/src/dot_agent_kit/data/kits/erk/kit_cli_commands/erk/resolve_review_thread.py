"""Resolve a PR review thread via GraphQL mutation.

This kit CLI command resolves a single PR review thread and outputs
JSON with the result.

Usage:
    dot-agent run erk resolve-review-thread --thread-id "PRRT_xxxx"

Output:
    JSON with success status

Exit Codes:
    0: Always (even on error, to support || true pattern)
    1: Context not initialized

Examples:
    $ dot-agent run erk resolve-review-thread --thread-id "PRRT_abc123"
    {"success": true, "thread_id": "PRRT_abc123"}

    $ dot-agent run erk resolve-review-thread --thread-id "invalid"
    {"success": false, "error_type": "resolution_failed", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass

import click

from dot_agent_kit.context_helpers import require_github, require_repo_root


@dataclass(frozen=True)
class ResolveThreadSuccess:
    """Success response for thread resolution."""

    success: bool
    thread_id: str


@dataclass(frozen=True)
class ResolveThreadError:
    """Error response for thread resolution."""

    success: bool
    error_type: str
    message: str


@click.command(name="resolve-review-thread")
@click.option("--thread-id", required=True, help="GraphQL node ID of the thread to resolve")
@click.pass_context
def resolve_review_thread(ctx: click.Context, thread_id: str) -> None:
    """Resolve a PR review thread.

    Takes a GraphQL node ID (from get-pr-review-comments output) and
    marks the thread as resolved.

    THREAD_ID: GraphQL node ID of the review thread
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

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
