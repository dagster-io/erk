"""Mark implementation started by updating GitHub issue metadata.

This exec command updates the plan-header metadata block in a GitHub issue
with the appropriate event fields based on the execution environment:
- Local machine: Updates last_local_impl_* fields (timestamp, event, session, user)
- GitHub Actions: Updates last_remote_impl_at field

Also writes .impl/local-run-state.json for fast local access (no GitHub API needed).

Usage:
    erk exec mark-impl-started

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk exec mark-impl-started
    {"success": true, "issue_number": 123}

    $ erk exec mark-impl-started
    {"success": false, "error_type": "no_issue_reference", "message": "..."}
"""

import getpass
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.env import in_github_actions
from erk_shared.impl_folder import read_plan_ref, write_local_run_state


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
@click.option(
    "--session-id",
    default=None,
    help="Session ID for tracking (passed from hooks/commands)",
)
@click.pass_context
def mark_impl_started(ctx: click.Context, session_id: str | None) -> None:
    """Update implementation started event in GitHub issue and local state file.

    Reads issue number from .impl/issue.json, fetches the issue from GitHub,
    updates the plan-header block with current event metadata, and posts back.

    Also writes .impl/local-run-state.json for fast local access.

    Detects execution environment:
    - Local machine: Updates last_local_impl_* fields (timestamp, event, session, user)
    - GitHub Actions: Updates last_remote_impl_at field

    Gracefully fails with exit code 0 to support || true pattern in slash commands.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)

    # Read plan reference from .impl/plan-ref.json (or legacy issue.json)
    impl_dir = cwd / ".impl"
    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is None:
        result = MarkImplError(
            success=False,
            error_type="no-issue-reference",
            message="No issue reference found in .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Capture metadata
    # session_id is passed as parameter, not from env var
    # (erk code never has access to CLAUDE_CODE_SESSION_ID env var)
    timestamp = datetime.now(UTC).isoformat()
    user = getpass.getuser()

    # Write local state file first (fast, no network)
    try:
        write_local_run_state(
            impl_dir=impl_dir,
            last_event="started",
            timestamp=timestamp,
            user=user,
            session_id=session_id,
        )
    except (FileNotFoundError, ValueError) as e:
        result = MarkImplError(
            success=False,
            error_type="local-state-write-failed",
            message=f"Failed to write local state: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Get PlanBackend from context
    try:
        backend = require_plan_backend(ctx)
    except SystemExit:
        result = MarkImplError(
            success=False,
            error_type="context-not-initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Update metadata directly via PlanBackend based on environment
    try:
        if in_github_actions():
            backend.update_metadata(
                repo_root,
                plan_ref.plan_id,
                metadata={"last_remote_impl_at": timestamp},
            )
        else:
            backend.update_metadata(
                repo_root,
                plan_ref.plan_id,
                metadata={
                    "last_local_impl_at": timestamp,
                    "last_local_impl_event": "started",
                    "last_local_impl_session": session_id,
                    "last_local_impl_user": user,
                },
            )
    except RuntimeError as e:
        result = MarkImplError(
            success=False,
            error_type="github-api-failed",
            message=f"Failed to update plan metadata: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    result_success = MarkImplSuccess(
        success=True,
        issue_number=int(plan_ref.plan_id),
    )
    click.echo(json.dumps(asdict(result_success), indent=2))
