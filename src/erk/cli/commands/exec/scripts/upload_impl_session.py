"""Upload current implementation session for async learn.

Replaces the inline bash logic in plan-implement.md Step 10b.
Reads plan reference from .impl/, captures session info, and uploads
using the same mechanism as upload-session.

Fixes the --issue-number vs --plan-id bug in the original bash.

Usage:
    erk exec upload-impl-session --session-id <id>

Output:
    JSON with upload result:
    {"uploaded": true, "plan_id": 2521}
    {"uploaded": false, "reason": "no_plan_tracking"}
    {"uploaded": false, "reason": "no_session_found"}

Exit Codes:
    0: Always (non-critical operation, graceful degradation)

Examples:
    $ erk exec upload-impl-session --session-id abc-123
    {"uploaded": true, "plan_id": 2521}
"""

import json
from datetime import UTC
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.capture_session_info import capture_session
from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.impl_folder import read_plan_ref
from erk_shared.plan_store.types import PlanNotFound


def _output_not_uploaded(reason: str) -> None:
    """Output a not-uploaded result and return."""
    click.echo(json.dumps({"uploaded": False, "reason": reason}))


@click.command(name="upload-impl-session")
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID to upload",
)
@click.pass_context
def upload_impl_session(ctx: click.Context, session_id: str) -> None:
    """Upload current implementation session for async learn.

    Reads plan reference from .impl/ to get the plan_id, captures
    session info from Claude installation, and uploads the session
    to a git branch for async learn processing.

    Always exits with code 0 (non-critical operation).
    """
    cwd = require_cwd(ctx)

    # Read plan reference from .impl/
    impl_dir = cwd / ".impl"
    if not impl_dir.exists():
        _output_not_uploaded("no_impl_folder")
        return

    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is None:
        _output_not_uploaded("no_plan_tracking")
        return

    if not plan_ref.plan_id.isdigit():
        _output_not_uploaded("non_numeric_plan_id")
        return

    plan_id = int(plan_ref.plan_id)

    # Capture session info
    try:
        installation = require_claude_installation(ctx)
    except SystemExit:
        _output_not_uploaded("no_claude_installation")
        return

    session_result = capture_session(cwd, installation)
    if session_result is None:
        _output_not_uploaded("no_session_found")
        return

    _session_id_from_file, session_file_str = session_result
    session_file = Path(session_file_str)
    if not session_file.exists():
        _output_not_uploaded("session_file_missing")
        return

    # Upload using the same mechanism as upload-session
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

    # Update plan metadata
    backend = require_plan_backend(ctx)
    plan_id_str = str(plan_id)
    timestamp = time.now().replace(tzinfo=UTC).isoformat()
    metadata: dict[str, object] = {
        "last_session_branch": session_branch,
        "last_session_id": session_id,
        "last_session_at": timestamp,
        "last_session_source": "local",
    }

    plan_result = backend.get_plan(repo_root, plan_id_str)
    if not isinstance(plan_result, PlanNotFound):
        try:
            backend.update_metadata(repo_root, plan_id_str, metadata)
        except RuntimeError:
            pass  # Non-critical: session branch was still created

    click.echo(json.dumps({"uploaded": True, "plan_id": plan_id}))
