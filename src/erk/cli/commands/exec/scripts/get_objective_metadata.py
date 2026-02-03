"""Extract arbitrary metadata fields from an objective issue's objective-header block.

Usage:
    erk exec get-objective-metadata <issue-number> <field-name>

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
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import find_metadata_block


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


@click.command(name="get-objective-metadata")
@click.argument("issue_number", type=int)
@click.argument("field_name")
@click.pass_context
def get_objective_metadata(
    ctx: click.Context,
    issue_number: int,
    field_name: str,
) -> None:
    """Extract a metadata field from an objective issue's objective-header block.

    Fetches the issue, extracts the objective-header block, and returns the
    specified field value. Returns null if the field doesn't exist.
    """
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch current issue
    issue = github_issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        result = MetadataError(
            success=False,
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1)

    # Extract objective-header block
    block = find_metadata_block(issue.body, "objective-header")
    if block is None:
        # No objective-header block - return null for the field
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
