"""Save plan as objective GitHub issue.

Usage:
    erk exec objective-save-to-issue [OPTIONS]

This command extracts a plan and creates a GitHub issue with:
- erk-plan + erk-objective labels (like extraction has erk-plan + erk-extraction)
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

    Creates a GitHub issue with erk-plan + erk-objective labels and plan content in body.
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # Get plan content
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
