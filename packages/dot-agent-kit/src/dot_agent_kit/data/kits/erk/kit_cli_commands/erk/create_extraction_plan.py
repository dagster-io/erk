"""Create extraction plan issue from file with proper metadata.

Usage:
    dot-agent run erk create-extraction-plan \
        --plan-file="/tmp/extraction-plan.md" \
        --source-plan-issues="123,456" \
        --extraction-session-ids="abc123,def456"

This command:
1. Creates GitHub issue with erk-plan + erk-extraction labels
2. Sets plan_type: extraction in plan-header metadata
3. Includes source_plan_issues and extraction_session_ids for tracking

Output:
    JSON with success status, issue_number, and issue_url
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


@click.command(name="create-extraction-plan")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to plan file to create issue from",
)
@click.option(
    "--source-plan-issues",
    type=str,
    default="",
    help="Comma-separated list of source plan issue numbers (e.g., '123,456')",
)
@click.option(
    "--extraction-session-ids",
    type=str,
    default="",
    help="Comma-separated list of session IDs that were analyzed (e.g., 'abc123,def456')",
)
@click.pass_context
def create_extraction_plan(
    ctx: click.Context,
    plan_file: Path,
    source_plan_issues: str,
    extraction_session_ids: str,
) -> None:
    """Create extraction plan issue from file with proper metadata.

    Reads plan content from file and creates a GitHub issue with:
    - erk-plan and erk-extraction labels
    - plan_type: extraction in metadata
    - Source tracking information
    """
    # Get GitHub Issues from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Read plan content from file
    plan_content = plan_file.read_text(encoding="utf-8").strip()
    if not plan_content:
        click.echo(json.dumps({"success": False, "error": "Empty plan content in file"}))
        raise SystemExit(1)

    # Parse source plan issues
    source_issues: list[int] = []
    if source_plan_issues:
        for part in source_plan_issues.split(","):
            part = part.strip()
            if part:
                try:
                    source_issues.append(int(part))
                except ValueError as e:
                    click.echo(
                        json.dumps(
                            {
                                "success": False,
                                "error": f"Invalid issue number: {part}",
                            }
                        )
                    )
                    raise SystemExit(1) from e

    # Parse session IDs
    session_ids: list[str] = []
    if extraction_session_ids:
        for part in extraction_session_ids.split(","):
            part = part.strip()
            if part:
                session_ids.append(part)

    # Validate: at least one session ID must be provided
    if not session_ids:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "At least one extraction_session_id is required",
                }
            )
        )
        raise SystemExit(1)

    # Get GitHub username
    username = github.get_current_username()
    if username is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "Could not get GitHub username (gh CLI not authenticated?)",
                }
            )
        )
        raise SystemExit(1)

    # Extract title from plan
    title = extract_title_from_plan(plan_content)

    # Prepare metadata with extraction plan fields
    created_at = datetime.now(UTC).isoformat()
    formatted_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
        plan_type="extraction",
        source_plan_issues=source_issues if source_issues else [],
        extraction_session_ids=session_ids,
    )

    # Ensure labels exist
    labels = ["erk-plan", "erk-extraction"]
    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-plan",
            description="Implementation plan for manual execution",
            color="0E8A16",
        )
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-extraction",
            description="Documentation extraction plan",
            color="D93F0B",
        )
    except RuntimeError as e:
        click.echo(json.dumps({"success": False, "error": f"Failed to ensure labels exist: {e}"}))
        raise SystemExit(1) from e

    # Create issue with [erk-extraction] suffix for visibility
    issue_title = f"{title} [erk-extraction]"
    try:
        result = github.create_issue(repo_root, issue_title, formatted_body, labels=labels)
    except RuntimeError as e:
        click.echo(json.dumps({"success": False, "error": f"Failed to create GitHub issue: {e}"}))
        raise SystemExit(1) from e

    # Add plan as first comment
    plan_comment = format_plan_content_comment(plan_content)
    try:
        github.add_comment(repo_root, result.number, plan_comment)
    except RuntimeError as e:
        # Issue created but comment failed - partial success
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Issue #{result.number} created but failed to add plan comment: {e}",
                    "issue_number": result.number,
                    "issue_url": result.url,
                }
            )
        )
        raise SystemExit(1) from e

    # Output success
    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": result.number,
                "issue_url": result.url,
                "title": title,
                "plan_type": "extraction",
                "source_plan_issues": source_issues,
                "extraction_session_ids": session_ids,
            }
        )
    )
