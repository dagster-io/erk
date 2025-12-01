"""Mark implementation started by updating GitHub issue metadata.

This kit CLI command updates the plan-header metadata block in a GitHub issue
with the appropriate timestamp field based on the execution environment:
- Local machine: Updates last_local_impl_at
- GitHub Actions: Updates last_remote_impl_at

This separation allows erk dash to show distinct timestamps for local vs remote runs.

Usage:
    dot-agent run erk mark-impl-started

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ dot-agent run erk mark-impl-started
    {"success": true, "issue_number": 123}

    $ dot-agent run erk mark-impl-started
    {"success": false, "error_type": "no_issue_reference", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.env import in_github_actions
from erk_shared.github.metadata import (
    update_plan_header_local_impl,
    update_plan_header_remote_impl,
)
from erk_shared.impl_folder import read_issue_reference

from dot_agent_kit.context_helpers import (
    require_github_issues,
    require_repo_root,
)


@dataclass(frozen=True)
class MarkImplSuccess:
    """Success response for mark impl started."""

    success: bool
    issue_number: int


@dataclass(frozen=True)
class MarkImplError:
    """Error response for mark impl started."""

    success: bool
    error_type: str
    message: str


@click.command(name="mark-impl-started")
@click.pass_context
def mark_impl_started(ctx: click.Context) -> None:
    """Update implementation timestamp in GitHub issue plan-header metadata.

    Reads issue number from .impl/issue.json, fetches the issue from GitHub,
    updates the plan-header block with current timestamp, and posts back.

    Detects execution environment:
    - Local machine: Updates last_local_impl_at field
    - GitHub Actions: Updates last_remote_impl_at field

    Gracefully fails with exit code 0 to support || true pattern in slash commands.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)

    # Read issue reference from .impl/issue.json
    impl_dir = Path.cwd() / ".impl"
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        result = MarkImplError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Get GitHub Issues from context
    try:
        github_issues = require_github_issues(ctx)
    except SystemExit:
        result = MarkImplError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Fetch current issue
    try:
        issue = github_issues.get_issue(repo_root, issue_ref.issue_number)
    except RuntimeError as e:
        result = MarkImplError(
            success=False,
            error_type="issue_not_found",
            message=f"Issue #{issue_ref.issue_number} not found: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Update impl timestamp based on environment
    timestamp = datetime.now(UTC).isoformat()
    try:
        if in_github_actions():
            updated_body = update_plan_header_remote_impl(
                issue_body=issue.body,
                remote_impl_at=timestamp,
            )
        else:
            updated_body = update_plan_header_local_impl(
                issue_body=issue.body,
                local_impl_at=timestamp,
            )
    except ValueError as e:
        # plan-header block not found (old format issue)
        result = MarkImplError(
            success=False,
            error_type="no_plan_header_block",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Update issue body
    try:
        github_issues.update_issue_body(repo_root, issue_ref.issue_number, updated_body)
    except RuntimeError as e:
        result = MarkImplError(
            success=False,
            error_type="github_api_failed",
            message=f"Failed to update issue body: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    result_success = MarkImplSuccess(
        success=True,
        issue_number=issue_ref.issue_number,
    )
    click.echo(json.dumps(asdict(result_success), indent=2))
