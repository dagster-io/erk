"""Extract arbitrary metadata fields from a plan issue's plan-header block.

Usage:
    erk exec get-plan-metadata <issue-number> <field-name>

Output:
    JSON with success status and field value (or null if field doesn't exist)

Exit Codes:
    0: Success (field found or null)
    1: Error (issue not found)
"""

import json
from dataclasses import asdict, dataclass
from typing import Any

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class MetadataSuccess:
    """Success response for metadata extraction."""

    success: bool
    value: Any
    issue_number: int
    field: str


@dataclass(frozen=True)
class MetadataError:
    """Error response for metadata extraction."""

    success: bool
    error: str
    message: str


@click.command(name="get-plan-metadata")
@click.argument("issue_number", type=int)
@click.argument("field_name")
@click.pass_context
def get_plan_metadata(
    ctx: click.Context,
    issue_number: int,
    field_name: str,
) -> None:
    """Extract a metadata field from a plan issue's plan-header block.

    Fetches the issue, extracts the plan-header block, and returns the
    specified field value. Returns null if the field doesn't exist.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    plan_id = str(issue_number)

    # Get metadata field via PlanBackend
    result = backend.get_metadata_field(repo_root, plan_id, field_name)
    if isinstance(result, PlanNotFound):
        error_result = MetadataError(
            success=False,
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )
        click.echo(json.dumps(asdict(error_result)), err=True)
        raise SystemExit(1)

    # result may be None for missing field or missing block, which is correct
    result_success = MetadataSuccess(
        success=True,
        value=result,
        issue_number=issue_number,
        field=field_name,
    )
    click.echo(json.dumps(asdict(result_success)))
