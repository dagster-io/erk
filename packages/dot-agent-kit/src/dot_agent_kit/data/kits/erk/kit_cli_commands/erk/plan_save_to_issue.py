"""Extract plan from ~/.claude/plans/ and create GitHub issue in one operation.

Usage:
    dot-agent run erk plan-save-to-issue [--format json|display] [--plan-file PATH]

This command combines plan extraction and issue creation:
1. Extract plan from specified file or latest from ~/.claude/plans/
2. Create GitHub issue with plan content (schema v2 format)

Output:
    --format json (default): {"success": true, "issue_number": N, ...}
    --format display: Formatted text ready for display

Exit Codes:
    0: Success - plan extracted and issue created
    1: Error - no plan found, gh failure, etc.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.metadata import (
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.plan_utils import extract_title_from_plan

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from dot_agent_kit.data.kits.erk.session_plan_extractor import get_latest_plan


@click.command(name="plan-save-to-issue")
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
    help="Path to specific plan file (default: most recent in ~/.claude/plans/)",
)
@click.pass_context
def plan_save_to_issue(ctx: click.Context, output_format: str, plan_file: Path | None) -> None:
    """Extract plan from ~/.claude/plans/ and create GitHub issue.

    Combines plan extraction and issue creation in a single operation.
    Uses schema v2 format (metadata in body, plan in first comment).
    """
    # Get GitHub Issues from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = Path.cwd()

    # Step 1: Extract plan from specified file or latest from ~/.claude/plans/
    if plan_file:
        plan = plan_file.read_text(encoding="utf-8")
    else:
        plan = get_latest_plan(str(cwd), session_id=None)

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

    # Step 2: Extract title
    title = extract_title_from_plan(plan)

    # Step 3: Get GitHub username
    username = github.get_current_username()
    if username is None:
        error_msg = "Could not get GitHub username (gh CLI not authenticated?)"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1)

    # Step 4: Prepare metadata (no worktree_name until worktree is created)
    created_at = datetime.now(UTC).isoformat()
    formatted_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
    )

    # Step 5: Ensure erk-plan label exists
    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-plan",
            description="Implementation plan for manual execution",
            color="0E8A16",
        )
    except RuntimeError as e:
        error_msg = f"Failed to ensure label exists: {e}"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1) from e

    # Step 6: Create issue (with [erk-plan] suffix for visibility)
    issue_title = f"{title} [erk-plan]"
    try:
        result = github.create_issue(repo_root, issue_title, formatted_body, labels=["erk-plan"])
    except RuntimeError as e:
        error_msg = f"Failed to create GitHub issue: {e}"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1) from e

    # Step 7: Add plan as first comment
    plan_comment = format_plan_content_comment(plan.strip())
    try:
        github.add_comment(repo_root, result.number, plan_comment)
    except RuntimeError as e:
        # Issue created but comment failed - partial success
        error_msg = f"Issue #{result.number} created but failed to add plan comment: {e}"
        if output_format == "display":
            click.echo(f"Warning: {error_msg}", err=True)
            click.echo(f"Please manually add plan content to: {result.url}", err=True)
        else:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": error_msg,
                        "issue_number": result.number,
                        "issue_url": result.url,
                    }
                )
            )
        raise SystemExit(1) from e

    # Step 8: Output success
    # Detect enrichment status for informational output
    is_enriched = "## Enrichment Details" in plan

    if output_format == "display":
        click.echo(f"Plan saved to GitHub issue #{result.number}")
        click.echo(f"URL: {result.url}")
        click.echo(f"Enrichment: {'Yes' if is_enriched else 'No'}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "issue_number": result.number,
                    "issue_url": result.url,
                    "title": title,
                    "enriched": is_enriched,
                }
            )
        )
