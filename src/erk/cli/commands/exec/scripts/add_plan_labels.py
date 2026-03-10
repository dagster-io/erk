"""Batch add labels to multiple plans.

Usage:
    echo '[{"pr_number": 42, "label": "erk-learn"}]' | erk exec add-plan-labels

Input:
    JSON array from stdin, each item: {"pr_number": int, "label": str}

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


class PlanLabelItem(TypedDict):
    """Type definition for a plan label item from stdin."""

    pr_number: int
    label: str


@dataclass(frozen=True)
class BatchLabelResult:
    """Batch label result."""

    success: bool
    results: list[dict[str, object]]


@dataclass(frozen=True)
class BatchLabelError:
    """Error response for batch label addition."""

    success: bool
    error_type: str
    message: str


def _validate_batch_input(data: object) -> list[PlanLabelItem] | BatchLabelError:
    """Validate that stdin JSON is a list of valid plan label items.

    Args:
        data: Parsed JSON object from stdin

    Returns:
        List of validated items, or BatchLabelError on validation failure
    """
    if not isinstance(data, list):
        return BatchLabelError(
            success=False,
            error_type="invalid-input",
            message="Input must be a JSON array",
        )

    validated_items: list[PlanLabelItem] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return BatchLabelError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} is not an object",
            )

        item_dict = cast("dict[str, Any]", item)

        if "pr_number" not in item_dict:
            return BatchLabelError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} missing required 'plan_number' field",
            )

        plan_number = item_dict["pr_number"]
        if not isinstance(plan_number, int):
            return BatchLabelError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} has non-integer 'plan_number'",
            )

        if "label" not in item_dict:
            return BatchLabelError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} missing required 'label' field",
            )

        label = item_dict["label"]
        if not isinstance(label, str):
            return BatchLabelError(
                success=False,
                error_type="invalid-input",
                message=f"Item at index {idx} has non-string 'label'",
            )

        validated_items.append({"pr_number": plan_number, "label": label})

    return validated_items


@click.command(name="add-plan-labels")
@click.pass_context
def add_plan_labels(ctx: click.Context) -> None:
    """Batch add labels to multiple plans from JSON stdin.

    Reads a JSON array from stdin where each item has:
    - pr_number (required): Plan PR number
    - label (required): Label to add

    Processes each plan sequentially and outputs batch results.
    Top-level success is true only if ALL labels were added successfully.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    # Read and parse stdin
    stdin = click.get_text_stream("stdin")
    try:
        raw_input = stdin.read()
        data = json.loads(raw_input)
    except json.JSONDecodeError as e:
        result = BatchLabelError(
            success=False,
            error_type="invalid-json",
            message=f"Failed to parse JSON: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Validate input structure
    validated = _validate_batch_input(data)
    if isinstance(validated, BatchLabelError):
        click.echo(json.dumps(asdict(validated), indent=2))
        raise SystemExit(0)

    # Process each plan sequentially
    results: list[dict[str, object]] = []

    for item in validated:
        plan_number = item["pr_number"]
        label = item["label"]
        plan_id = str(plan_number)

        try:
            backend.add_label(repo_root, plan_id, label)
        except RuntimeError as e:
            results.append(
                {
                    "pr_number": plan_number,
                    "success": False,
                    "error": f"Failed to add label: {e}",
                }
            )
            continue

        results.append(
            {
                "pr_number": plan_number,
                "success": True,
                "label": label,
            }
        )

    # Output batch result
    batch_result = BatchLabelResult(
        success=all(r.get("success", False) for r in results),
        results=results,
    )
    click.echo(json.dumps(asdict(batch_result), indent=2))
    raise SystemExit(0)
