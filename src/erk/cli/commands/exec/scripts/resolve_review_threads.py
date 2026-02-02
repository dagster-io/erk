"""Resolve multiple PR review threads via batch JSON stdin.

This exec command resolves multiple PR review threads in one invocation
and outputs JSON with batch results. Reuses the same core logic as
resolve-review-thread.

Usage:
    echo '[{"thread_id": "PRRT_1", "comment": "Fixed"}]' | erk exec resolve-review-threads

Input:
    JSON array from stdin, each item: {"thread_id": str, "comment": str | null}

Output:
    JSON with batch results

Exit Codes:
    0: Always (even on error, to support || true pattern)
    1: Context not initialized

Examples:
    $ echo '[{"thread_id": "PRRT_abc"}]' | erk exec resolve-review-threads
    {"success": true, "results": [{"success": true, ...}]}

    $ echo '[{"thread_id": "PRRT_abc", "comment": "Fixed"}]' | erk exec resolve-review-threads
    {"success": true, "results": [{"success": true, "comment_added": true}]}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, TypedDict, cast

import click

from erk.cli.commands.exec.scripts.resolve_review_thread import _resolve_single
from erk_shared.context.helpers import require_github, require_repo_root

if TYPE_CHECKING:
    from typing import Any


class ThreadResolutionItem(TypedDict):
    """Type definition for a thread resolution item from stdin."""

    thread_id: str
    comment: str | None


@dataclass(frozen=True)
class BatchResolveResult:
    """Batch resolution result."""

    success: bool
    results: list[dict[str, object]]


@dataclass(frozen=True)
class BatchResolveError:
    """Error response for batch resolution."""

    success: bool
    error_type: str
    message: str


def _validate_batch_input(data: object) -> list[ThreadResolutionItem] | BatchResolveError:
    """Validate that stdin JSON is a list of valid thread resolution items.

    Args:
        data: Parsed JSON object from stdin

    Returns:
        List of validated items, or BatchResolveError on validation failure
    """
    if not isinstance(data, list):
        return BatchResolveError(
            success=False,
            error_type="invalid-input",
            message="Input must be a JSON array",
        )

    validated_items: list[ThreadResolutionItem] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return BatchResolveError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} is not an object",
            )

        # Cast to dict[str, Any] after isinstance check for type narrowing
        item_dict = cast("dict[str, Any]", item)

        if "thread_id" not in item_dict:
            return BatchResolveError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} missing required 'thread_id' field",
            )

        thread_id = item_dict["thread_id"]
        if not isinstance(thread_id, str):
            return BatchResolveError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} has non-string 'thread_id'",
            )

        comment = item_dict.get("comment")
        if comment is not None and not isinstance(comment, str):
            return BatchResolveError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} has non-string 'comment'",
            )

        validated_items.append({"thread_id": thread_id, "comment": comment})

    return validated_items


@click.command(name="resolve-review-threads")
@click.pass_context
def resolve_review_threads(ctx: click.Context) -> None:
    """Resolve multiple PR review threads from JSON stdin.

    Reads a JSON array from stdin where each item has:
    - thread_id (required): GraphQL node ID of the thread
    - comment (optional): Comment to add before resolving

    Processes each thread sequentially and outputs batch results.
    Top-level success is true only if ALL threads resolved successfully.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Read and parse stdin
    stdin = click.get_text_stream("stdin")
    try:
        raw_input = stdin.read()
        data = json.loads(raw_input)
    except json.JSONDecodeError as e:
        result = BatchResolveError(
            success=False,
            error_type="invalid-json",
            message=f"Failed to parse JSON: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Validate input structure
    validated = _validate_batch_input(data)
    if isinstance(validated, BatchResolveError):
        click.echo(json.dumps(asdict(validated), indent=2))
        raise SystemExit(0)

    # Process each thread sequentially
    results: list[dict[str, object]] = []

    for item in validated:
        single_result = _resolve_single(github, repo_root, item["thread_id"], item.get("comment"))
        results.append(asdict(single_result))

    # Output batch result
    batch_result = BatchResolveResult(
        success=all(r.get("success", False) for r in results),
        results=results,
    )
    click.echo(json.dumps(asdict(batch_result), indent=2))
    raise SystemExit(0)
