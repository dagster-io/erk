"""Upload preprocessed session files to a secret GitHub gist.

This exec script handles the session upload phase of `erk land --learn`:
1. Finds sessions for the plan issue using find_sessions_for_plan()
2. Filters to locally readable sessions using get_readable_sessions()
3. Preprocesses each session to XML format
4. Uploads all files to a secret gist via gh gist create

Usage:
    erk exec upload-learn-sessions --plan-issue 123 --session-id abc-123

Output:
    JSON object with upload results:
    {
        "success": true,
        "gist_url": "https://gist.github.com/...",
        "gist_id": "abc123...",
        "session_count": 3,
        "files": ["planning-abc.xml", "impl-def.xml", ...]
    }

Exit Codes:
    0: Success (even with 0 sessions - valid result)
    1: Error (GitHub failure, etc.)
"""

import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_claude_installation,
    require_issues,
    require_repo_root,
)
from erk_shared.sessions.discovery import (
    find_sessions_for_plan,
    get_readable_sessions,
)


@dataclass(frozen=True)
class UploadSuccess:
    """Success result for upload-learn-sessions command."""

    success: bool
    gist_url: str
    gist_id: str
    session_count: int
    files: list[str]


@dataclass(frozen=True)
class UploadNoSessions:
    """Result when no sessions are available to upload."""

    success: bool
    gist_url: str | None
    gist_id: str | None
    session_count: int
    message: str


@dataclass(frozen=True)
class UploadError:
    """Error result when upload fails."""

    success: bool
    error: str


def _preprocess_session(
    session_path: Path,
    session_id: str,
    output_dir: Path,
    prefix: str,
) -> list[Path]:
    """Preprocess a session file to XML format.

    Uses erk exec preprocess-session to convert JSONL to compressed XML.
    Returns list of output file paths (may be multiple if chunked).

    Args:
        session_path: Path to the session JSONL file
        session_id: Session ID for filtering
        output_dir: Directory to write output files
        prefix: Prefix for output filenames

    Returns:
        List of output file paths
    """
    result = subprocess.run(
        [
            "erk",
            "exec",
            "preprocess-session",
            str(session_path),
            "--session-id",
            session_id,
            "--max-tokens",
            "20000",
            "--output-dir",
            str(output_dir),
            "--prefix",
            prefix,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    # Parse output - each line is a file path
    output_files: list[Path] = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line:
            path = Path(line)
            if path.exists():
                output_files.append(path)

    return output_files


def _upload_to_gist(files: list[Path], description: str) -> tuple[str, str] | None:
    """Upload files to a secret GitHub gist.

    Args:
        files: List of file paths to upload
        description: Gist description

    Returns:
        Tuple of (gist_url, gist_id) or None on failure
    """
    if not files:
        return None

    cmd = ["gh", "gist", "create", "--desc", description]
    for f in files:
        cmd.append(str(f))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    # gh gist create outputs the URL
    gist_url = result.stdout.strip()
    if not gist_url:
        return None

    # Extract gist ID from URL (last path component)
    gist_id = gist_url.rstrip("/").split("/")[-1]

    return gist_url, gist_id


@click.command(name="upload-learn-sessions")
@click.option(
    "--plan-issue",
    "plan_issue",
    type=int,
    required=True,
    help="Plan issue number",
)
@click.option(
    "--session-id",
    "current_session_id",
    type=str,
    required=True,
    help="Current session ID (for output directory)",
)
@click.pass_context
def upload_learn_sessions(
    ctx: click.Context,
    *,
    plan_issue: int,
    current_session_id: str,
) -> None:
    """Upload preprocessed session files to a secret gist.

    Finds sessions associated with the plan issue, preprocesses them to XML,
    and uploads to a secret GitHub gist for remote learn workflow access.

    Outputs JSON with gist URL and file information.
    """
    # Get dependencies
    github_issues = require_issues(ctx)
    claude_installation = require_claude_installation(ctx)
    repo_root = require_repo_root(ctx)

    # Find sessions for the plan
    sessions_for_plan = find_sessions_for_plan(
        github_issues,
        repo_root,
        plan_issue,
    )

    # Get readable sessions
    readable_sessions = get_readable_sessions(
        sessions_for_plan,
        claude_installation,
    )

    if not readable_sessions:
        # No sessions to upload - this is valid (remote learn will analyze PR diff only)
        result = UploadNoSessions(
            success=True,
            gist_url=None,
            gist_id=None,
            session_count=0,
            message="No local sessions found for plan",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        return

    # Create temp directory for preprocessed files
    with tempfile.TemporaryDirectory(prefix="learn-upload-") as temp_dir:
        output_dir = Path(temp_dir)
        all_files: list[Path] = []

        # Preprocess each session
        for session_id, session_path in readable_sessions:
            # Determine prefix based on session type
            if session_id == sessions_for_plan.planning_session_id:
                prefix = "planning"
            elif session_id in sessions_for_plan.implementation_session_ids:
                prefix = "impl"
            else:
                prefix = "session"

            files = _preprocess_session(
                session_path,
                session_id,
                output_dir,
                prefix,
            )
            all_files.extend(files)

        if not all_files:
            # Preprocessing failed for all sessions
            result = UploadNoSessions(
                success=True,
                gist_url=None,
                gist_id=None,
                session_count=0,
                message="Session preprocessing produced no output",
            )
            click.echo(json.dumps(asdict(result), indent=2))
            return

        # Upload to gist
        gist_result = _upload_to_gist(
            all_files,
            f"Learn materials for plan #{plan_issue}",
        )

        if gist_result is None:
            error = UploadError(
                success=False,
                error="Failed to create gist",
            )
            click.echo(json.dumps(asdict(error), indent=2))
            raise SystemExit(1)

        gist_url, gist_id = gist_result

        success = UploadSuccess(
            success=True,
            gist_url=gist_url,
            gist_id=gist_id,
            session_count=len(readable_sessions),
            files=[f.name for f in all_files],
        )
        click.echo(json.dumps(asdict(success), indent=2))
