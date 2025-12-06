"""Create extraction plan issue from file or content with proper metadata.

Usage (new - preferred):
    dot-agent run erk create-extraction-plan \
        --plan-content="# Plan Title..." \
        --session-id="abc123" \
        --extraction-session-ids="abc123,def456"

Usage (legacy - file path):
    dot-agent run erk create-extraction-plan \
        --plan-file=".erk/scratch/<session-id>/extraction-plan.md" \
        --source-plan-issues="123,456" \
        --extraction-session-ids="abc123,def456"

The --plan-content option is preferred because it:
1. Automatically writes to .erk/scratch/<session-id>/extraction-plan.md
2. Prevents agents from accidentally using /tmp/

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
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, delete_marker
from erk_shared.scratch.scratch import write_scratch_file

from dot_agent_kit.context_helpers import require_cwd, require_github_issues, require_repo_root


@click.command(name="create-extraction-plan")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to plan file to create issue from (use --plan-content instead)",
)
@click.option(
    "--plan-content",
    type=str,
    default=None,
    help="Plan content to create issue from (preferred over --plan-file)",
)
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Session ID for scratch directory (required with --plan-content)",
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
    plan_file: Path | None,
    plan_content: str | None,
    session_id: str | None,
    source_plan_issues: str,
    extraction_session_ids: str,
) -> None:
    """Create extraction plan issue from content or file with proper metadata.

    Reads plan content from --plan-content or --plan-file and creates a GitHub issue with:
    - erk-plan and erk-extraction labels
    - plan_type: extraction in metadata
    - Source tracking information

    When using --plan-content, the content is automatically written to
    .erk/scratch/<session-id>/extraction-plan.md
    """
    # Get required context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)

    # Validate options: must provide either --plan-content or --plan-file
    if plan_content is None and plan_file is None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "Must provide either --plan-content or --plan-file",
                }
            )
        )
        raise SystemExit(1)

    if plan_content is not None and plan_file is not None:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "Cannot provide both --plan-content and --plan-file",
                }
            )
        )
        raise SystemExit(1)

    # Handle --plan-content: requires --session-id, writes to scratch
    if plan_content is not None:
        if session_id is None:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "--session-id is required when using --plan-content",
                    }
                )
            )
            raise SystemExit(1)

        # Write to scratch directory
        scratch_path = write_scratch_file(
            plan_content,
            session_id=session_id,
            suffix=".md",
            prefix="extraction-plan-",
            repo_root=repo_root,
        )
        content = plan_content.strip()
    else:
        # Handle --plan-file: read content from file
        # plan_file is guaranteed to be not None here
        assert plan_file is not None  # for type checker
        content = plan_file.read_text(encoding="utf-8").strip()
        scratch_path = None

    if not content:
        click.echo(json.dumps({"success": False, "error": "Empty plan content"}))
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
    title = extract_title_from_plan(content)

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
    plan_comment = format_plan_content_comment(content)
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

    # Delete pending extraction marker since extraction is complete
    delete_marker(cwd, PENDING_EXTRACTION_MARKER)

    # Output success
    output: dict[str, object] = {
        "success": True,
        "issue_number": result.number,
        "issue_url": result.url,
        "title": title,
        "plan_type": "extraction",
        "source_plan_issues": source_issues,
        "extraction_session_ids": session_ids,
    }
    if scratch_path is not None:
        output["scratch_path"] = str(scratch_path)
    click.echo(json.dumps(output))
