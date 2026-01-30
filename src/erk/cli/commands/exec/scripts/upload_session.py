"""Upload a Claude Code session to GitHub Gist and update the plan header.

This exec command uploads a session JSONL file to a GitHub Gist and optionally
updates the plan-header metadata in the associated erk-plan issue.

Usage:
    # Upload from local session file
    erk exec upload-session --session-file /path/to/session.jsonl \\
        --session-id abc-123 --source local

    # Upload and update plan issue
    erk exec upload-session --session-file /path/to/session.jsonl \\
        --session-id abc-123 --source remote --issue-number 2521

Output:
    Structured JSON output with gist info and updated plan header fields

Exit Codes:
    0: Success (gist created and optionally plan header updated)
    1: Error (gist creation failed, issue update failed)

Examples:
    $ erk exec upload-session --session-file session.jsonl \\
          --session-id abc --source remote --issue-number 123
    {
      "success": true,
      "gist_id": "abc123...",
      "gist_url": "https://gist.github.com/user/abc123...",
      "raw_url": "https://gist.githubusercontent.com/...",
      "session_id": "abc",
      "issue_number": 123,
      "issue_updated": true
    }
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_github, require_issues, require_repo_root
from erk_shared.gateway.github.abc import GistCreateError
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import BodyText


@click.command(name="upload-session")
@click.option(
    "--session-file",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the session JSONL file to upload",
)
@click.option(
    "--session-id",
    required=True,
    help="Claude Code session ID",
)
@click.option(
    "--source",
    required=True,
    type=click.Choice(["local", "remote"]),
    help="Session source: 'local' or 'remote'",
)
@click.option(
    "--issue-number",
    type=int,
    help="Optional erk-plan issue number to update with gist info",
)
@click.pass_context
def upload_session(
    ctx: click.Context,
    session_file: Path,
    session_id: str,
    source: Literal["local", "remote"],
    issue_number: int | None,
) -> None:
    """Upload a session JSONL to GitHub Gist and update plan header.

    Creates a secret gist containing the session JSONL file, then optionally
    updates the plan-header metadata in the associated erk-plan issue with
    the gist URL and session information.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Read session content
    session_content = session_file.read_text(encoding="utf-8")

    # Create gist with descriptive info
    description = f"Claude Code session {session_id} ({source})"
    filename = f"session-{session_id}.jsonl"

    gist_result = github.create_gist(
        filename=filename,
        content=session_content,
        description=description,
        public=False,  # Secret gist for privacy
    )

    if isinstance(gist_result, GistCreateError):
        error_output = {
            "success": False,
            "error": f"Failed to create gist: {gist_result.message}",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    # Build base result
    result: dict[str, object] = {
        "success": True,
        "gist_id": gist_result.gist_id,
        "gist_url": gist_result.gist_url,
        "raw_url": gist_result.raw_url,
        "session_id": session_id,
    }

    # Update plan issue if requested
    if issue_number is not None:
        result["issue_number"] = issue_number

        # Import here to avoid circular imports
        from erk_shared.gateway.github.metadata.plan_header import (
            update_plan_header_session_gist,
        )

        # Get current issue body
        issues = require_issues(ctx)
        issue_info = issues.get_issue(repo_root, issue_number)
        if isinstance(issue_info, IssueNotFound):
            msg = f"Issue #{issue_number} not found"
            raise RuntimeError(msg)
        issue_body = issue_info.body

        # Update with session gist info
        timestamp = datetime.now(UTC).isoformat()
        try:
            updated_body = update_plan_header_session_gist(
                issue_body=issue_body,
                gist_url=gist_result.gist_url,
                gist_id=gist_result.gist_id,
                session_id=session_id,
                session_at=timestamp,
                source=source,
            )
            issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
            result["issue_updated"] = True
        except (ValueError, RuntimeError) as e:
            # Issue update failed but gist was created - partial success
            result["issue_updated"] = False
            result["issue_update_error"] = str(e)

    click.echo(json.dumps(result))
