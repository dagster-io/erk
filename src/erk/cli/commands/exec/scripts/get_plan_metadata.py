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

from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.context.helpers import require_repo_root
from erk_shared.github.metadata.core import find_metadata_block


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
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch current issue
    try:
        issue = github_issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        result = MetadataError(
            success=False,
            error="issue_not_found",
            message=f"Issue #{issue_number} not found: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    # Extract plan-header block
    block = find_metadata_block(issue.body, "plan-header")
    if block is None:
        # No plan-header block - return null for the field
        result_success = MetadataSuccess(
            success=True,
            value=None,
            issue_number=issue_number,
            field=field_name,
        )
        click.echo(json.dumps(asdict(result_success)))
        return

    # Get field value (None if field doesn't exist)
    field_value = block.data.get(field_name)

    result_success = MetadataSuccess(
        success=True,
        value=field_value,
        issue_number=issue_number,
        field=field_name,
    )
    click.echo(json.dumps(asdict(result_success)))
