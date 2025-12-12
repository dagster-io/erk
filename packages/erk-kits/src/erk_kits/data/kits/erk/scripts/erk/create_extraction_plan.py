"""Create extraction plan issue from file or content with proper metadata.

Usage (new - preferred):
    erk kit exec erk create-extraction-plan \
        --plan-content="# Plan Title..." \
        --session-id="abc123" \
        --extraction-session-ids="abc123,def456"

Usage (legacy - file path):
    erk kit exec erk create-extraction-plan \
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
from pathlib import Path

import click

from erk.kits.context_helpers import require_github_issues
from erk.kits.operations.agent_docs import check_docs_agent_ready
from erk_shared.context.helpers import require_cwd, require_repo_root
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, delete_marker
from erk_shared.scratch.scratch import write_scratch_file


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

    # Validate docs/agent is ready before creating extraction plans
    is_ready, warning = check_docs_agent_ready(repo_root)
    if not is_ready:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": warning,
                    "suggestion": "Run 'erk docs init' first",
                }
            )
        )
        raise SystemExit(1)

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

    # Use consolidated create_plan_issue for the entire workflow
    result = create_plan_issue(
        github_issues=github,
        repo_root=repo_root,
        plan_content=content,
        plan_type="extraction",
        source_plan_issues=source_issues if source_issues else None,
        extraction_session_ids=session_ids,
    )

    if not result.success:
        if result.issue_number is not None:
            # Partial success - issue created but comment failed
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
        else:
            click.echo(json.dumps({"success": False, "error": result.error}))
        raise SystemExit(1)

    # Delete pending extraction marker since extraction is complete
    delete_marker(cwd, PENDING_EXTRACTION_MARKER)

    # Output success
    output: dict[str, object] = {
        "success": True,
        "issue_number": result.issue_number,
        "issue_url": result.issue_url,
        "title": result.title,
        "plan_type": "extraction",
        "source_plan_issues": source_issues,
        "extraction_session_ids": session_ids,
    }
    if scratch_path is not None:
        output["scratch_path"] = str(scratch_path)
    click.echo(json.dumps(output))
