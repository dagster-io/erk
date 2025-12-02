"""Update workflow run_id in GitHub issue plan-header metadata.

This kit CLI command is designed to be called from within a GitHub Actions
workflow immediately after checkout. It updates the plan-header block with
the current workflow run_id, enabling trigger_workflow() to poll for it.

Usage:
    dot-agent run erk update-workflow-run-id <issue-number> <run-id>

Output:
    JSON with success status

Exit Codes:
    0: Success
    1: Error (issue not found, no plan-header block)
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import click
from erk_shared.github.metadata import (
    MetadataBlock,
    PlanHeaderSchema,
    find_metadata_block,
    render_metadata_block,
    replace_metadata_block_in_body,
)

from dot_agent_kit.context_helpers import (
    require_github_issues,
    require_repo_root,
)


@dataclass(frozen=True)
class UpdateSuccess:
    """Success response for workflow run_id update."""

    success: bool
    issue_number: int
    run_id: str


@dataclass(frozen=True)
class UpdateError:
    """Error response for workflow run_id update."""

    success: bool
    error: str
    message: str


@click.command(name="update-workflow-run-id")
@click.argument("issue_number", type=int)
@click.argument("run_id")
@click.pass_context
def update_workflow_run_id(
    ctx: click.Context,
    issue_number: int,
    run_id: str,
) -> None:
    """Update workflow run_id in GitHub issue plan-header metadata.

    Fetches the issue, updates the plan-header block with last_dispatched_run_id
    and last_dispatched_at, and posts the updated body back to GitHub.

    This is called from within GitHub Actions workflows immediately after
    checkout to enable trigger_workflow() to poll for the run_id.
    """
    # Get dependencies from context
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch current issue
    try:
        issue = github_issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="issue_not_found",
            message=f"Issue #{issue_number} not found: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    # Find plan-header block
    block = find_metadata_block(issue.body, "plan-header")
    if block is None:
        result = UpdateError(
            success=False,
            error="no_plan_header_block",
            message="plan-header block not found in issue body",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    # Update run_id and timestamp
    updated_data = dict(block.data)
    updated_data["last_dispatched_run_id"] = run_id
    updated_data["last_dispatched_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    updated_body = replace_metadata_block_in_body(issue.body, "plan-header", new_block_content)

    # Update issue body
    try:
        github_issues.update_issue_body(repo_root, issue_number, updated_body)
    except RuntimeError as e:
        result = UpdateError(
            success=False,
            error="github_api_failed",
            message=f"Failed to update issue body: {e}",
        )
        click.echo(json.dumps(asdict(result)), err=True)
        raise SystemExit(1) from None

    result_success = UpdateSuccess(
        success=True,
        issue_number=issue_number,
        run_id=run_id,
    )
    click.echo(json.dumps(asdict(result_success)))
