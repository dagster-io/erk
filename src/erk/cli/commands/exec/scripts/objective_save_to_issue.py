"""Save plan as objective GitHub issue.

Usage:
    erk exec objective-save-to-issue [OPTIONS]

This command extracts a plan and creates a GitHub issue with:
- erk-objective label only (NOT erk-plan - objectives are not plans)
- No title suffix
- Plan content directly in body (no metadata block)
- No commands section

Options:
    --session-id ID: Session ID for scoped plan lookup
    --format: json (default) or display

Exit Codes:
    0: Success - objective issue created
    1: Error - no plan found, gh failure, etc.
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_repo_root,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.github.plan_issues import create_objective_issue
from erk_shared.scratch.scratch import get_scratch_dir


def _create_objective_saved_issue_marker(
    session_id: str, repo_root: Path, issue_number: int
) -> None:
    """Create marker file storing the issue number of the saved objective.

    This marker enables idempotency - when the agent calls objective-save-to-issue
    multiple times in the same session, subsequent calls return the existing issue
    instead of creating duplicates.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.
        issue_number: The GitHub issue number where the objective was saved.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "objective-saved-issue.marker"
    marker_file.write_text(str(issue_number), encoding="utf-8")


def _get_existing_saved_objective(session_id: str, repo_root: Path) -> int | None:
    """Check if this session already saved an objective and return the issue number.

    This prevents duplicate objective creation when the agent calls
    objective-save-to-issue multiple times in the same session.

    Args:
        session_id: The session ID for the scratch directory.
        repo_root: The repository root path.

    Returns:
        The issue number if objective was already saved, None otherwise.
    """
    marker_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = marker_dir / "objective-saved-issue.marker"
    if not marker_file.exists():
        return None
    content = marker_file.read_text(encoding="utf-8").strip()
    if not content.isdigit():
        return None
    return int(content)


@click.command(name="objective-save-to-issue")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.option(
    "--session-id",
    default=None,
    help="Session ID for scoped plan lookup",
)
@click.pass_context
def objective_save_to_issue(ctx: click.Context, output_format: str, session_id: str | None) -> None:
    """Save plan as objective GitHub issue.

    Creates a GitHub issue with only the erk-objective label (NOT erk-plan).
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # Session deduplication check
    # Prevent duplicate objective creation when the agent calls objective-save-to-issue
    # multiple times in the same session
    if session_id is not None:
        existing_issue = _get_existing_saved_objective(session_id, repo_root)
        if existing_issue is not None:
            if output_format == "display":
                click.echo(
                    f"This session already saved objective #{existing_issue}. "
                    "Skipping duplicate creation.",
                    err=True,
                )
            else:
                click.echo(
                    json.dumps(
                        {
                            "success": True,
                            "issue_number": existing_issue,
                            "skipped_duplicate": True,
                            "message": f"Session already saved objective #{existing_issue}",
                        }
                    )
                )
            return

    # Get plan content - priority: scratch directory > Claude plans directory
    plan: str | None = None

    # Priority 1: Check scratch directory for session-scoped plan
    if session_id is not None:
        scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
        scratch_plan_path = scratch_dir / "plan.md"
        if scratch_plan_path.exists():
            plan = scratch_plan_path.read_text(encoding="utf-8")

    # Priority 2: Fall back to Claude installation lookup
    if plan is None:
        plan = claude_installation.get_latest_plan(cwd, session_id=session_id)

    if not plan:
        if output_format == "display":
            click.echo("Error: No plan found in ~/.claude/plans/", err=True)
            click.echo("\nTo fix:", err=True)
            click.echo("1. Create a plan (enter Plan mode if needed)", err=True)
            click.echo("2. Exit Plan mode using ExitPlanMode tool", err=True)
            click.echo("3. Run this command again", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": "No plan found in ~/.claude/plans/"}))
        raise SystemExit(1)

    # Create objective issue
    result = create_objective_issue(
        github_issues=github,
        repo_root=repo_root,
        plan_content=plan,
        title=None,
        extra_labels=None,
    )

    if not result.success:
        if output_format == "display":
            click.echo(f"Error: {result.error}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": result.error}))
        raise SystemExit(1)

    # Guard for type narrowing
    if result.issue_number is None:
        raise RuntimeError("Unexpected: issue_number is None after success")

    # Create marker file to enable idempotency
    if session_id is not None:
        _create_objective_saved_issue_marker(session_id, repo_root, result.issue_number)

    if output_format == "display":
        click.echo(f"Objective saved to GitHub issue #{result.issue_number}")
        click.echo(f"Title: {result.title}")
        click.echo(f"URL: {result.issue_url}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": result.issue_number,
                    "issue_url": result.issue_url,
                    "title": result.title,
                }
            )
        )
