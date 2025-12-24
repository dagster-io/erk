"""Update plan content in an existing GitHub issue.

Usage:
    erk kit exec erk plan-update-issue ISSUE_NUMBER [OPTIONS]

This command updates the plan content in a Schema v2 issue:
1. Find the plan file (from --plan-file, --session-id, or default lookup)
2. Get the issue's first comment (plan content per Schema v2)
3. Update that comment with the new plan content

Options:
    ISSUE_NUMBER: Issue number to update (required)
    --plan-file PATH: Use specific plan file (highest priority)
    --session-id ID: Use session-scoped lookup to find plan by slug
    (neither): Fall back to most recent plan by modification time

Output:
    --format json (default): {"success": true, "issue_number": N, ...}
    --format display: Formatted text ready for display

Exit Codes:
    0: Success - plan updated
    1: Error - no plan found, issue not found, gh failure, etc.
"""

import json
from pathlib import Path

import click

from erk.kits.context_helpers import require_github_issues
from erk_shared.context.helpers import (
    require_cwd,
    require_repo_root,
    require_session_store,
)
from erk_shared.github.plan_issues import update_plan_issue


@click.command(name="plan-update-issue")
@click.argument("issue_number", type=int)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to specific plan file (highest priority)",
)
@click.option(
    "--session-id",
    default=None,
    help="Session ID for scoped plan lookup (uses slug from session logs)",
)
@click.pass_context
def plan_update_issue(
    ctx: click.Context,
    issue_number: int,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
) -> None:
    """Update plan content in existing GitHub issue.

    ISSUE_NUMBER is the GitHub issue number to update.
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    session_store = require_session_store(ctx)

    # Step 1: Extract plan (priority: plan_file > session_id > most recent)
    if plan_file:
        plan = plan_file.read_text(encoding="utf-8")
    else:
        plan = session_store.get_latest_plan(cwd, session_id=session_id)

    if not plan:
        if output_format == "display":
            click.echo("Error: No plan found in ~/.claude/plans/", err=True)
            click.echo("\nTo fix:", err=True)
            click.echo("1. Create a plan (enter Plan mode if needed)", err=True)
            click.echo("2. Exit Plan mode using ExitPlanMode tool", err=True)
            click.echo("3. Run this command again", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": "No plan found in ~/.claude/plans/"}))
        raise SystemExit(1) from None

    # Step 2: Update the issue
    result = update_plan_issue(
        github_issues=github,
        repo_root=repo_root,
        issue_number=issue_number,
        plan_content=plan,
    )

    if not result.success:
        if output_format == "display":
            click.echo(f"Error: {result.error}", err=True)
        else:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": result.error,
                        "issue_number": result.issue_number,
                        "issue_url": result.issue_url,
                    }
                )
            )
        raise SystemExit(1) from None

    # Success output
    if output_format == "display":
        click.echo(f"Plan updated in GitHub issue #{result.issue_number}")
        click.echo(f"URL: {result.issue_url}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": result.issue_number,
                    "issue_url": result.issue_url,
                }
            )
        )
