"""Track learn evaluation completion on a plan.

This exec script posts a tracking comment to the plan and updates
the plan-header metadata block to record that learn evaluation was performed.
It replaces the tracking side-effect in `erk learn --no-interactive`.

Usage:
    erk exec track-learn-evaluation <plan-number> --session-id="..."

Output:
    JSON object with tracking result:
    {
        "success": true,
        "pr_number": 123,
        "tracked": true
    }

Exit Codes:
    0: Success
    1: Error (invalid plan, GitHub failure, etc.)
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.learn.tracking import track_learn_invocation
from erk_shared.plan_store.types import PlanHeaderNotFoundError


@dataclass(frozen=True)
class TrackLearnResult:
    """Result of track-learn-evaluation command."""

    success: bool
    pr_number: int
    tracked: bool


@dataclass(frozen=True)
class TrackLearnError:
    """Error result when tracking fails."""

    success: bool
    error: str
    message: str


def _extract_pr_number(identifier: str) -> int | None:
    """Extract PR number from identifier (number or URL).

    Args:
        identifier: Plan number or GitHub issue URL

    Returns:
        PR number or None if invalid
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
    backend,
    repo_root: Path,
    pr_number: int,
    session_id: str | None,
    time: Time,
) -> None:
    """Post tracking comment and update plan-header on the plan.

    Args:
        backend: ManagedPrBackend interface for metadata updates and comments
        repo_root: Repository root path
        pr_number: Plan number
        session_id: Session ID invoking learn (optional)
        time: Time gateway for testable timestamps
    """
    # Note: We pass 0 for readable_count and total_count since this script
    # is called after session discovery - the tracking comment is just a marker
    # that learn evaluation happened, not detailed session counts.
    track_learn_invocation(
        backend,
        repo_root,
        str(pr_number),
        session_id=session_id,
        readable_count=0,
        total_count=0,
    )

    # Update plan-header with learn event (in addition to comment)
    timestamp = time.now().replace(tzinfo=UTC).isoformat()
    try:
        backend.update_metadata(
            repo_root,
            str(pr_number),
            metadata={
                "last_learn_at": timestamp,
                "last_learn_session": session_id,
            },
        )
    except PlanHeaderNotFoundError:
        error = TrackLearnError(
            success=False,
            error="no-metadata-block",
            message=(
                f"PR #{pr_number} has no plan-header metadata block"
                " — cannot update learn evaluation"
            ),
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1) from None
    except RuntimeError as e:
        error = TrackLearnError(
            success=False,
            error="github-api-failed",
            message=f"Failed to track learn evaluation on PR #{pr_number}: {e}",
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1) from None


@click.command(name="track-learn-evaluation")
@click.argument("issue", type=str, required=False)
@click.option(
    "--session-id",
    default=None,
    help="Session ID for tracking (passed from Claude session context)",
)
@click.pass_context
def track_learn_evaluation(ctx: click.Context, issue: str | None, session_id: str | None) -> None:
    """Track learn evaluation completion on a plan.

    ISSUE can be a plan number (e.g., "123") or a full GitHub URL.
    If not provided, infers from .erk/impl-context/plan-ref.json on the current branch.

    Posts a tracking comment to record that learn was invoked.
    """
    # Get dependencies from context
    backend = require_plan_backend(ctx)
    git = require_git(ctx)
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    time = require_time(ctx)

    # Resolve PR number: explicit argument or infer from branch
    pr_number: int | None = None
    if issue is not None:
        pr_number = _extract_pr_number(issue)
        if pr_number is None:
            error = TrackLearnError(
                success=False,
                error="invalid-plan-identifier",
                message=f"Invalid plan identifier: {issue}",
            )
            click.echo(json.dumps(asdict(error)))
            raise SystemExit(1)
    else:
        # Try to infer from current branch
        branch = git.branch.get_current_branch(cwd)
        if branch is not None:
            pr_id_str = backend.resolve_pr_number_for_branch(repo_root, branch)
            if pr_id_str is not None:
                pr_number = int(pr_id_str)

    if pr_number is None:
        error = TrackLearnError(
            success=False,
            error="no-plan-specified",
            message="No PR specified and could not infer from branch name",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Post tracking comment and update metadata
    _do_track(
        backend=backend,
        repo_root=repo_root,
        pr_number=pr_number,
        session_id=session_id,
        time=time,
    )

    result = TrackLearnResult(
        success=True,
        pr_number=pr_number,
        tracked=True,
    )

    click.echo(json.dumps(asdict(result), indent=2))
