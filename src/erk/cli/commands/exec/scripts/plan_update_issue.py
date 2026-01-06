"""Update an existing GitHub issue's plan comment with new content.

Usage:
    erk exec plan-update-issue --issue-number N [OPTIONS]

This command updates the plan content comment on an existing GitHub issue:
1. Find plan file (from session scratch, --plan-path, or ~/.claude/plans/)
2. Get the first comment ID from the issue (where plan body lives)
3. Update that comment with new plan content

Options:
    --issue-number N: GitHub issue number to update (required)
    --session-id ID: Session ID to find plan file in scratch storage
    --plan-path PATH: Direct path to plan file (overrides session lookup)

Output:
    --format json (default): {"success": true, ...}
    --format display: Formatted text

Exit Codes:
    0: Success - plan comment updated
    1: Error - issue not found, no plan found, no comments, etc.
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
from erk_shared.github.metadata.plan_header import format_plan_content_comment


@click.command(name="plan-update-issue")
@click.option(
    "--issue-number",
    type=int,
    required=True,
    help="GitHub issue number to update",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.option(
    "--plan-path",
    type=click.Path(exists=True, path_type=Path),
    help="Direct path to plan file (overrides session lookup)",
)
@click.option(
    "--session-id",
    help="Session ID to find plan file in scratch storage",
)
@click.pass_context
def plan_update_issue(
    ctx: click.Context,
    *,
    issue_number: int,
    output_format: str,
    plan_path: Path | None,
    session_id: str | None,
) -> None:
    """Update an existing GitHub issue's plan comment with new content."""
    # Get dependencies from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # Step 1: Find plan content (priority: plan_path > session > latest)
    if plan_path is not None:
        plan_content = plan_path.read_text(encoding="utf-8")
    else:
        plan_content = claude_installation.get_latest_plan(cwd, session_id=session_id)

    if not plan_content:
        error_msg = "No plan found in ~/.claude/plans/"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1)

    # Step 2: Get existing issue to verify it exists
    try:
        issue = github.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        error_msg = f"Failed to get issue #{issue_number}: {e}"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1) from e

    # Step 3: Get first comment ID (where plan body lives in Schema v2)
    comments = github.get_issue_comments_with_urls(repo_root, issue_number)
    if not comments:
        error_msg = f"Issue #{issue_number} has no comments - cannot update plan content"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1)

    first_comment = comments[0]
    comment_id = first_comment.id

    # Step 4: Format plan content and update comment
    formatted_plan = format_plan_content_comment(plan_content.strip())

    try:
        github.update_comment(repo_root, comment_id, formatted_plan)
    except RuntimeError as e:
        error_msg = f"Failed to update comment: {e}"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1) from e

    # Step 5: Output success
    if output_format == "display":
        click.echo(f"Plan updated on issue #{issue_number}")
        click.echo(f"Title: {issue.title}")
        click.echo(f"URL: {issue.url}")
        click.echo(f"Comment: {first_comment.url}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": issue_number,
                    "issue_url": issue.url,
                    "comment_id": comment_id,
                    "comment_url": first_comment.url,
                }
            )
        )
