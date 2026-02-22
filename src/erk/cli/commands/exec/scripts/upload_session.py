"""Upload a Claude Code session to a git branch and update the plan header.

This exec command creates an `async-learn/{plan_id}` branch, commits the session
JSONL file to `.erk/session/{session_id}.jsonl`, and optionally updates the
plan-header metadata in the associated erk-plan issue.

Usage:
    # Upload from local session file
    erk exec upload-session --session-file /path/to/session.jsonl \\
        --session-id abc-123 --source local --plan-id 2521

    # Upload and update plan issue
    erk exec upload-session --session-file /path/to/session.jsonl \\
        --session-id abc-123 --source remote --plan-id 2521

Output:
    Structured JSON output with branch info and updated plan header fields

Exit Codes:
    0: Success (branch created and optionally plan header updated)
    1: Error (branch creation failed, issue update failed)

Examples:
    $ erk exec upload-session --session-file session.jsonl \\
          --session-id abc --source remote --plan-id 123
    {
      "success": true,
      "session_branch": "async-learn/123",
      "session_id": "abc",
      "plan_id": 123,
      "issue_updated": true
    }
"""

import json
from datetime import UTC
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import (
    require_git,
    require_plan_backend,
    require_repo_root,
    require_time,
)
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
    "--plan-id",
    type=int,
    help="Plan identifier to create session branch and update plan header",
)
@click.pass_context
def upload_session(
    ctx: click.Context,
    session_file: Path,
    session_id: str,
    source: Literal["local", "remote"],
    plan_id: int | None,
) -> None:
    """Upload a session JSONL to a git branch and update plan header.

    Creates an async-learn/{plan_id} branch from origin/master, commits the session
    JSONL to .erk/session/{session_id}.jsonl, then updates the plan-header
    metadata in the associated plan with the branch name and session information.
    """
    if plan_id is None:
        error_output = {
            "success": False,
            "error": "--plan-id is required for branch-based session upload",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    time = require_time(ctx)

    session_branch = f"async-learn/{plan_id}"

    # Delete existing local session branch if it exists (re-implementation idempotency)
    git.branch.delete_branch(repo_root, session_branch, force=True)

    # Create session branch from origin/master (no checkout needed)
    git.branch.create_branch(repo_root, session_branch, "origin/master", force=False)

    # Commit session file directly to branch using git plumbing (no checkout)
    session_content = session_file.read_text(encoding="utf-8")
    git.commit.commit_files_to_branch(
        repo_root,
        branch=session_branch,
        files={f".erk/session/{session_id}.jsonl": session_content},
        message=f"Session {session_id} for plan #{plan_id}",
    )

    # Force-push (does not require branch to be checked out)
    git.remote.push_to_remote(repo_root, "origin", session_branch, set_upstream=True, force=True)

    # Build base result
    result: dict[str, object] = {
        "success": True,
        "session_branch": session_branch,
        "session_id": session_id,
        "plan_id": plan_id,
    }

    # Update plan metadata
    backend = require_plan_backend(ctx)
    plan_id_str = str(plan_id)
    timestamp = time.now().replace(tzinfo=UTC).isoformat()
    metadata: dict[str, object] = {
        "last_session_branch": session_branch,
        "last_session_id": session_id,
        "last_session_at": timestamp,
        "last_session_source": source,
    }

    # LBYL: Check plan exists before updating
    plan_result = backend.get_plan(repo_root, plan_id_str)
    if isinstance(plan_result, PlanNotFound):
        # Plan not found but branch was created - partial success
        result["issue_updated"] = False
        result["issue_update_error"] = f"Plan #{plan_id} not found"
    else:
        try:
            backend.update_metadata(repo_root, plan_id_str, metadata)
            result["issue_updated"] = True
        except RuntimeError as e:
            # Plan update failed but branch was created - partial success
            result["issue_updated"] = False
            result["issue_update_error"] = str(e)

    click.echo(json.dumps(result))
