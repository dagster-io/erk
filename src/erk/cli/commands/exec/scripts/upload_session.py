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
from datetime import UTC
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import (
    require_github,
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.gateway.github.abc import GistCreateError
from erk_shared.plan_store.types import PlanNotFound


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
    time = require_time(ctx)

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

        backend = require_plan_backend(ctx)
        plan_id = str(issue_number)
        timestamp = time.now().replace(tzinfo=UTC).isoformat()
        metadata: dict[str, object] = {
            "last_session_gist_url": gist_result.gist_url,
            "last_session_gist_id": gist_result.gist_id,
            "last_session_id": session_id,
            "last_session_at": timestamp,
            "last_session_source": source,
        }

        # LBYL: Check plan exists before updating
        plan_result = backend.get_plan(repo_root, plan_id)
        if isinstance(plan_result, PlanNotFound):
            # Issue not found but gist was created - partial success
            result["issue_updated"] = False
            result["issue_update_error"] = f"Issue #{issue_number} not found"
        else:
            try:
                backend.update_metadata(repo_root, plan_id, metadata)
                result["issue_updated"] = True
            except RuntimeError as e:
                # Issue update failed but gist was created - partial success
                result["issue_updated"] = False
                result["issue_update_error"] = str(e)

    click.echo(json.dumps(result))
