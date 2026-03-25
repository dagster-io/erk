"""Extract arbitrary metadata fields from a PR's plan-header block.

Usage:
    erk exec get-pr-metadata <pr-number> <field-name>

Output:
    JSON with success status and field value (or null if field doesn't exist)

Exit Codes:
    0: Success (field found or null)
    1: Error (PR not found)
"""

import json
from dataclasses import asdict, dataclass
from typing import Any

import click

from erk.cli.pr_ref_type import PR_REF
from erk_shared.context.helpers import require_pr_backend, require_repo_root
from erk_shared.pr_store.types import PrNotFound


@dataclass(frozen=True)
class MetadataSuccess:
    """Success response for metadata extraction."""

    success: bool
    value: Any
    pr_number: int
    field: str


@dataclass(frozen=True)
class MetadataError:
    """Error response for metadata extraction."""

    success: bool
    error: str
    message: str


@click.command(name="get-pr-metadata")
@click.argument("pr", type=PR_REF)
@click.argument("field_name")
@click.pass_context
def get_pr_metadata(
    ctx: click.Context,
    pr: int,
    field_name: str,
) -> None:
    """Extract a metadata field from a PR's plan-header block.

    Fetches the issue, extracts the plan-header block, and returns the
    specified field value. Returns null if the field doesn't exist.
    """
    backend = require_pr_backend(ctx)
    repo_root = require_repo_root(ctx)

    pr_id = str(pr)

    # Get metadata field via ManagedPrBackend
    result = backend.get_metadata_field(repo_root, pr_id, field_name)
    if isinstance(result, PrNotFound):
        error_result = MetadataError(
            success=False,
            error="issue_not_found",
            message=f"PR #{pr} not found",
        )
        click.echo(json.dumps(asdict(error_result)), err=True)
        raise SystemExit(1)

    # result may be None for missing field or missing block, which is correct
    result_success = MetadataSuccess(
        success=True,
        value=result,
        pr_number=pr,
        field=field_name,
    )
    click.echo(json.dumps(asdict(result_success)))
