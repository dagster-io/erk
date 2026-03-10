"""Fetch preprocessed sessions from a planned-pr-context branch.

Downloads the manifest and XML files from the planned-pr-context/{plan_id} branch
for use by the learn pipeline. Returns JSON with file list and manifest metadata.

Usage:
    erk exec fetch-sessions --plan-id 2521 --output-dir ./learn

Output:
    Structured JSON output:
    {"success": true, "pr_number": 2521, "manifest": {...}, "files": [...]}
    {"success": false, "error": "branch_not_found"}

Exit Codes:
    0: Success
    1: Error (branch not found, fetch failed)
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import require_git, require_repo_root
from erk_shared.gateway.git.abc import Git
from erk_shared.sessions.manifest import read_session_manifest


def _fetch_file_from_branch(
    *,
    repo_root: Path,
    session_branch: str,
    filename: str,
    output_dir: Path,
    git: Git,
) -> Path | None:
    """Fetch a single file from the branch via git show.

    Args:
        repo_root: Repository root path.
        session_branch: Branch name to read from.
        filename: Filename within .erk/sessions/ on the branch.
        output_dir: Directory to write the file to.
        git: Git gateway instance.

    Returns:
        Path to the written file, or None on failure.
    """
    raw = git.commit.read_file_from_ref(
        repo_root,
        ref=f"origin/{session_branch}",
        file_path=f".erk/sessions/{filename}",
    )
    if raw is None:
        return None

    output_file = output_dir / filename
    output_file.write_bytes(raw)
    return output_file


@click.command(name="fetch-sessions")
@click.option(
    "--pr-number",
    required=True,
    type=int,
    help="PR identifier to fetch sessions for",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to write fetched XML files",
)
@click.pass_context
def fetch_sessions(
    ctx: click.Context,
    pr_number: int,
    output_dir: Path,
) -> None:
    """Fetch preprocessed sessions from a planned-pr-context branch.

    Reads the manifest from the planned-pr-context/{pr_number} branch and downloads
    all XML files to the output directory.
    """
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    session_branch = f"planned-pr-context/{pr_number}"

    # Check if branch exists on remote
    if not git.branch.branch_exists_on_remote(repo_root, "origin", session_branch):
        click.echo(json.dumps({"success": False, "error": "branch_not_found"}))
        raise SystemExit(1)

    # Fetch the branch
    git.remote.fetch_branch(repo_root, "origin", session_branch)

    # Read manifest
    manifest = read_session_manifest(git, repo_root=repo_root, session_branch=session_branch)
    if manifest is None:
        click.echo(json.dumps({"success": False, "error": "manifest_not_found"}))
        raise SystemExit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download each XML file referenced in manifest
    downloaded_files: list[str] = []
    sessions = manifest.get("sessions", [])
    for session_entry in sessions:
        for filename in session_entry.get("files", []):
            fetched = _fetch_file_from_branch(
                repo_root=repo_root,
                session_branch=session_branch,
                filename=filename,
                output_dir=output_dir,
                git=git,
            )
            if fetched is not None:
                downloaded_files.append(str(fetched))

    result: dict[str, object] = {
        "success": True,
        "pr_number": pr_number,
        "session_branch": session_branch,
        "manifest": manifest,
        "files": downloaded_files,
    }
    click.echo(json.dumps(result))
