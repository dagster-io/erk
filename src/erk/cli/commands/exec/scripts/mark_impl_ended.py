"""Mark implementation ended by updating GitHub issue metadata.

This exec command updates the plan-header metadata block in a GitHub issue
with the appropriate event fields based on the execution environment:
- Local machine: Updates last_local_impl_* fields (timestamp, event="ended", session, user)
- GitHub Actions: Updates last_remote_impl_at field

Also writes .impl/local-run-state.json for fast local access (no GitHub API needed).

Usage:
    erk exec mark-impl-ended

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk exec mark-impl-ended
    {"success": true, "issue_number": 123}

    $ erk exec mark-impl-ended
    {"success": false, "error_type": "no_issue_reference", "message": "..."}
"""

import getpass
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_repo_root,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.env import in_github_actions
from erk_shared.github.metadata import (
    update_plan_header_local_impl_event,
    update_plan_header_remote_impl,
)
from erk_shared.impl_folder import read_issue_reference, write_local_run_state


@dataclass(frozen=True)
class MarkImplSuccess:
    """Success response for mark impl ended."""

    success: bool
    issue_number: int


@dataclass(frozen=True)
class MarkImplError:
    """Error response for mark impl ended."""

    success: bool
    error_type: str
    message: str


@click.command(name="mark-impl-ended")
@click.pass_context
def mark_impl_ended(ctx: click.Context) -> None:
    """Update implementation ended event in GitHub issue and local state file.

    Reads issue number from .impl/issue.json, fetches the issue from GitHub,
    updates the plan-header block with current event metadata, and posts back.

    Also writes .impl/local-run-state.json for fast local access.

    Detects execution environment:
    - Local machine: Updates last_local_impl_* fields (timestamp, event="ended", session, user)
    - GitHub Actions: Updates last_remote_impl_at field

    Gracefully fails with exit code 0 to support || true pattern in slash commands.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)

    # Read issue reference from .impl/issue.json
    impl_dir = cwd / ".impl"
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        result = MarkImplError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Capture metadata
    timestamp = datetime.now(UTC).isoformat()
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
    user = getpass.getuser()

    # Write local state file first (fast, no network)
    try:
        write_local_run_state(
            impl_dir=impl_dir,
            last_event="ended",
            timestamp=timestamp,
            user=user,
            session_id=session_id,
        )
    except (FileNotFoundError, ValueError) as e:
        result = MarkImplError(
            success=False,
            error_type="local_state_write_failed",
            message=f"Failed to write local state: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

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

    # Update impl event based on environment
    try:
        if in_github_actions():
            updated_body = update_plan_header_remote_impl(
                issue_body=issue.body,
                remote_impl_at=timestamp,
            )
        else:
            updated_body = update_plan_header_local_impl_event(
                issue_body=issue.body,
                local_impl_at=timestamp,
                event="ended",
                session_id=session_id,
                user=user,
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
