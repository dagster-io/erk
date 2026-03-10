"""Batch close multiple plan PRs with comments.

Usage:
    echo '[{"pr_number": 42, "comment": "Superseded"}]' | erk exec close-prs

Input:
    JSON array from stdin, each item: {"pr_number": int, "comment": str}

Output:
    JSON with batch results

Exit Codes:
    0: Always (even on error, to support batch contract)
    1: Context not initialized
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, TypedDict, cast

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root

if TYPE_CHECKING:
    from typing import Any


class PlanCloseItem(TypedDict):
    """Type definition for a plan close item from stdin."""

    pr_number: int
    comment: str


@dataclass(frozen=True)
class BatchCloseResult:
    """Batch close result."""

    success: bool
    results: list[dict[str, object]]


@dataclass(frozen=True)
class BatchCloseError:
    """Error response for batch close."""

    success: bool
    error_type: str
    message: str


def _validate_batch_input(data: object) -> list[PlanCloseItem] | BatchCloseError:
    """Validate that stdin JSON is a list of valid plan close items.

    Args:
        data: Parsed JSON object from stdin

    Returns:
        List of validated items, or BatchCloseError on validation failure
    """
    if not isinstance(data, list):
        return BatchCloseError(
            success=False,
            error_type="invalid-input",
            message="Input must be a JSON array",
        )

    validated_items: list[PlanCloseItem] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return BatchCloseError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} is not an object",
            )

        item_dict = cast("dict[str, Any]", item)

        if "pr_number" not in item_dict:
            return BatchCloseError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} missing required 'pr_number' field",
            )

        pr_number = item_dict["pr_number"]
        if not isinstance(pr_number, int):
            return BatchCloseError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} has non-integer 'pr_number'",
            )

        if "comment" not in item_dict:
            return BatchCloseError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} missing required 'comment' field",
            )

        comment = item_dict["comment"]
        if not isinstance(comment, str):
            return BatchCloseError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} has non-string 'comment'",
            )

        validated_items.append({"pr_number": pr_number, "comment": comment})

    return validated_items


@click.command(name="close-prs")
@click.pass_context
def close_prs(ctx: click.Context) -> None:
    """Batch close multiple plan PRs with comments from JSON stdin.

    Reads a JSON array from stdin where each item has:
    - pr_number (required): Plan PR number
    - comment (required): Comment to add before closing

    Processes each plan sequentially and outputs batch results.
    Top-level success is true only if ALL plans closed successfully.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    # Read and parse stdin
    stdin = click.get_text_stream("stdin")
    try:
        raw_input = stdin.read()
        data = json.loads(raw_input)
    except json.JSONDecodeError as e:
        result = BatchCloseError(
            success=False,
            error_type="invalid-json",
            message=f"Failed to parse JSON: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Validate input structure
    validated = _validate_batch_input(data)
    if isinstance(validated, BatchCloseError):
        click.echo(json.dumps(asdict(validated), indent=2))
        raise SystemExit(0)

    # Process each plan sequentially
    results: list[dict[str, object]] = []

    for item in validated:
        pr_number = item["pr_number"]
        comment = item["comment"]
        pr_id = str(pr_number)

        try:
            comment_id = backend.add_comment(repo_root, pr_id, comment)
        except RuntimeError as e:
            results.append(
                {
                    "pr_number": pr_number,
                    "success": False,
                    "error": f"Failed to add comment: {e}",
                }
            )
            continue

        try:
            backend.close_plan(repo_root, pr_id)
        except RuntimeError as e:
            results.append(
                {
                    "pr_number": pr_number,
                    "success": False,
                    "error": f"Failed to close PR: {e}",
                    "comment_id": comment_id,
                }
            )
            continue

        results.append(
            {
                "pr_number": pr_number,
                "success": True,
                "comment_id": comment_id,
            }
        )

    # Output batch result
    batch_result = BatchCloseResult(
        success=all(r.get("success", False) for r in results),
        results=results,
    )
    click.echo(json.dumps(asdict(batch_result), indent=2))
    raise SystemExit(0)
