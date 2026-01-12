"""Track learn evaluation completion on a plan issue.

This exec script posts a tracking comment to the plan issue and updates
the plan-header metadata block to record that learn evaluation was performed.
It replaces the tracking side-effect in `erk learn --no-interactive`.

Usage:
    erk exec track-learn-evaluation <issue-number> --session-id="..."

Output:
    JSON object with tracking result:
    {
        "success": true,
        "issue_number": 123,
        "tracked": true
    }

Exit Codes:
    0: Success
    1: Error (invalid issue, GitHub failure, etc.)
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_issues,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.github.metadata.plan_header import update_plan_header_learn_event
from erk_shared.learn.tracking import track_learn_invocation
from erk_shared.naming import extract_leading_issue_number


@dataclass(frozen=True)
class TrackLearnResult:
    """Result of track-learn-evaluation command."""

    success: bool
    issue_number: int
    tracked: bool


@dataclass(frozen=True)
class TrackLearnError:
    """Error result when tracking fails."""

    success: bool
    error: str


def _extract_issue_number(identifier: str) -> int | None:
    """Extract issue number from identifier (number or URL).

    Args:
        identifier: Issue number or GitHub issue URL

    Returns:
        Issue number or None if invalid
    """
    # Try direct number (LBYL: check before converting)
    if identifier.isdigit():
        return int(identifier)

    # Try URL format: https://github.com/owner/repo/issues/123
    if "/issues/" in identifier:
        parts = identifier.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            return int(parts[-1])

    return None


def _do_track(
    *,
    github_issues,
    repo_root: Path,
    issue_number: int,
    session_id: str | None,
    time: Time,
) -> None:
    """Post tracking comment and update plan-header on the plan issue.

    Args:
        github_issues: GitHub issues interface
        repo_root: Repository root path
        issue_number: Plan issue number
        session_id: Session ID invoking learn (optional)
        time: Time gateway for testable timestamps
    """
    # Note: We pass 0 for readable_count and total_count since this script
    # is called after session discovery - the tracking comment is just a marker
    # that learn evaluation happened, not detailed session counts.
    track_learn_invocation(
        github_issues,
        repo_root,
        issue_number,
        session_id=session_id,
        readable_count=0,
        total_count=0,
    )

    # Update plan-header with learn event (in addition to comment)
    timestamp = time.now().replace(tzinfo=UTC).isoformat()
    issue = github_issues.get_issue(repo_root, issue_number)
    updated_body = update_plan_header_learn_event(
        issue_body=issue.body,
        learn_at=timestamp,
        session_id=session_id,
    )
    github_issues.update_issue_body(repo_root, issue_number, updated_body)


@click.command(name="track-learn-evaluation")
@click.argument("issue", type=str, required=False)
@click.option(
    "--session-id",
    default=None,
    help="Session ID for tracking (passed from Claude session context)",
)
@click.pass_context
def track_learn_evaluation(ctx: click.Context, issue: str | None, session_id: str | None) -> None:
    """Track learn evaluation completion on a plan issue.

    ISSUE can be a plan issue number (e.g., "123") or a full GitHub URL.
    If not provided, infers from current branch name (P{issue}-...).

    Posts a tracking comment to record that learn was invoked.
    """
    # Get dependencies from context
    github_issues = require_issues(ctx)
    git = require_git(ctx)
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    time = require_time(ctx)

    # Resolve issue number: explicit argument or infer from branch
    issue_number: int | None = None
    if issue is not None:
        issue_number = _extract_issue_number(issue)
        if issue_number is None:
            error = TrackLearnError(
                success=False,
                error=f"Invalid issue identifier: {issue}",
            )
            click.echo(json.dumps(asdict(error)))
            raise SystemExit(1)
    else:
        # Try to infer from current branch
        branch = git.get_current_branch(cwd)
        if branch is not None:
            issue_number = extract_leading_issue_number(branch)

    if issue_number is None:
        error = TrackLearnError(
            success=False,
            error="No issue specified and could not infer from branch name",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Post tracking comment
    _do_track(
        github_issues=github_issues,
        repo_root=repo_root,
        issue_number=issue_number,
        session_id=session_id,
        time=time,
    )

    result = TrackLearnResult(
        success=True,
        issue_number=issue_number,
        tracked=True,
    )

    click.echo(json.dumps(asdict(result), indent=2))
