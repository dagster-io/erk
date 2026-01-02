"""Update plan content in an existing GitHub issue.

Usage:
    erk exec plan-update-issue --issue NUMBER [OPTIONS]

This command updates the plan content in an existing erk plan issue:
1. Read plan from specified file, session-scoped lookup, or stdin
2. Extract plan_comment_id from issue's plan-header
3. Update the comment with new plan content

Options:
    --issue NUMBER: Required. The issue number to update.
    --plan-file PATH: Use specific plan file
    --session-id ID: Use session-scoped lookup to find plan by slug
    (neither): Read from stdin

Output:
    --format json (default): {"success": true, "issue_number": N, ...}
    --format display: Formatted text ready for display

Exit Codes:
    0: Success - plan updated
    1: Error - issue not found, no plan content, etc.
"""

import json
import sys
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_repo_root,
    require_session_store,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.github.plan_issues import update_plan_issue_content


@click.command(name="plan-update-issue")
@click.option(
    "--issue",
    required=True,
    type=int,
    help="Issue number to update",
)
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
    help="Path to specific plan file",
)
@click.option(
    "--session-id",
    help="Session ID for scoped plan lookup (uses slug from session logs)",
)
@click.pass_context
def plan_update_issue(
    ctx: click.Context,
    issue: int,
    output_format: str,
    plan_file: Path | None,
    session_id: str | None,
) -> None:
    """Update plan content in an existing GitHub issue.

    Updates the plan content stored in the first comment of an erk plan issue.
    """
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    session_store = require_session_store(ctx)

    # Determine plan content source (priority: plan_file > session_id > stdin)
    plan_content: str | None = None

    if plan_file is not None:
        plan_content = plan_file.read_text(encoding="utf-8")
    elif session_id is not None:
        plan_content = session_store.get_latest_plan(cwd, session_id=session_id)
    elif not sys.stdin.isatty():
        # Read from stdin if not a TTY
        plan_content = sys.stdin.read()

    if not plan_content:
        if output_format == "display":
            click.echo("Error: No plan content provided.", err=True)
            click.echo("\nUsage:", err=True)
            click.echo("  erk exec plan-update-issue --issue NUMBER --plan-file PATH", err=True)
            click.echo("  erk exec plan-update-issue --issue NUMBER --session-id ID", err=True)
            click.echo("  cat plan.md | erk exec plan-update-issue --issue NUMBER", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": "No plan content provided"}))
        raise SystemExit(1)

    # Update the plan issue
    result = update_plan_issue_content(
        github_issues=github,
        repo_root=repo_root,
        issue_number=issue,
        new_plan_content=plan_content,
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
                        "comment_id": result.comment_id,
                    }
                )
            )
        raise SystemExit(1)

    # Success output
    if output_format == "display":
        click.echo(f"Plan updated in issue #{result.issue_number}")
        click.echo(f"Comment ID: {result.comment_id}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": result.issue_number,
                    "comment_id": result.comment_id,
                }
            )
        )
