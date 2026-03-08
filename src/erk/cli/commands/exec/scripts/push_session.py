"""Push a preprocessed session to the planned-pr-context branch with accumulation.

Preprocesses session JSONL to compressed XML and accumulates multiple sessions
on the same branch across lifecycle stages.

Usage:
    erk exec push-session \\
        --session-file /path/to/session.jsonl \\
        --session-id abc-123 \\
        --stage planning \\
        --source local \\
        --plan-id 2521

Output:
    Structured JSON output with upload status:
    {"uploaded": true, "plan_id": 2521, "session_branch": "planned-pr-context/2521", "files": [...]}
    {"uploaded": false, "reason": "preprocessing_failed"}

Exit Codes:
    0: Always (non-critical operation, graceful degradation)
"""

import json
import subprocess
import tempfile
from dataclasses import dataclass
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
from erk_shared.gateway.git.abc import Git
from erk_shared.learn.extraction.session_schema import (
    iter_jsonl_entries,
    parse_session_timestamp,
)
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class SessionProvenance:
    """Lightweight provenance stats computed before preprocessing."""

    user_turns: int
    duration_minutes: int | None
    raw_size_kb: int


def _has_user_text(message_content: str | list) -> bool:
    """Check if message content contains non-empty user text."""
    if isinstance(message_content, list):
        return any(
            isinstance(block, dict)
            and block.get("type") == "text"
            and block.get("text", "").strip()
            for block in message_content
        )
    if isinstance(message_content, str):
        return bool(message_content.strip())
    return False


def _compute_session_provenance(session_file: Path) -> SessionProvenance | None:
    """Compute lightweight provenance stats from a session JSONL file.

    Reads the JSONL to count user turns and compute duration from timestamps.
    Does not run the full preprocessing pipeline.

    Args:
        session_file: Path to the session JSONL file.

    Returns:
        SessionProvenance with stats, or None if the file cannot be read.
    """
    if not session_file.exists():
        return None

    content = session_file.read_text(encoding="utf-8")
    raw_size_kb = session_file.stat().st_size // 1024

    timestamps: list[float] = []
    user_turns = 0
    for entry in iter_jsonl_entries(content):
        ts = parse_session_timestamp(entry.get("timestamp"))
        if ts is not None:
            timestamps.append(ts)
        if entry.get("type") == "user":
            msg_content = entry.get("message", {}).get("content", "")
            if _has_user_text(msg_content):
                user_turns += 1

    duration_minutes: int | None = None
    if len(timestamps) >= 2:
        duration_seconds = max(timestamps) - min(timestamps)
        duration_minutes = round(duration_seconds / 60)

    return SessionProvenance(
        user_turns=user_turns,
        duration_minutes=duration_minutes,
        raw_size_kb=raw_size_kb,
    )


def _preprocess_session(
    *,
    session_file: Path,
    stage: str,
    session_id: str,
    repo_root: Path,
) -> list[Path] | None:
    """Run preprocess-session to convert JSONL to compressed XML.

    Args:
        session_file: Path to the session JSONL file.
        stage: Lifecycle stage (planning, impl, address).
        session_id: Session ID for the prefix.
        repo_root: Repository root for running the command.

    Returns:
        List of XML file paths on success, None on failure.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = f"{stage}-{session_id}"
        result = subprocess.run(
            [
                "erk",
                "exec",
                "preprocess-session",
                str(session_file),
                "--max-tokens",
                "20000",
                "--output-dir",
                tmpdir,
                "--prefix",
                prefix,
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None

        # Collect generated XML files
        tmpdir_path = Path(tmpdir)
        xml_files = sorted(tmpdir_path.glob("*.xml"))
        if not xml_files:
            return None

        # Copy files to a persistent location (tmpdir will be cleaned up)
        persistent_dir = repo_root / ".erk" / "scratch" / "push-session"
        persistent_dir.mkdir(parents=True, exist_ok=True)
        persistent_files: list[Path] = []
        for xml_file in xml_files:
            dest = persistent_dir / xml_file.name
            dest.write_bytes(xml_file.read_bytes())
            persistent_files.append(dest)

        return persistent_files


def _read_manifest_from_branch(
    *,
    repo_root: Path,
    session_branch: str,
    git: Git,
) -> dict | None:
    """Read existing manifest from the remote branch via git show.

    Args:
        repo_root: Repository root path.
        session_branch: Branch name to read from.
        git: Git gateway instance.

    Returns:
        Parsed manifest dict if found, None otherwise.
    """
    raw = git.commit.read_file_from_ref(
        repo_root,
        ref=f"origin/{session_branch}",
        file_path=".erk/sessions/manifest.json",
    )
    if raw is None:
        return None
    content = raw.decode("utf-8").strip()
    if not content:
        return None
    return json.loads(content)


def _build_manifest_entry(
    *,
    session_id: str,
    stage: str,
    source: str,
    timestamp: str,
    filenames: list[str],
    provenance: SessionProvenance | None,
    xml_size_kb: int | None,
    git_branch: str | None,
) -> dict:
    """Build a manifest entry for a session upload."""
    entry: dict[str, object] = {
        "session_id": session_id,
        "stage": stage,
        "source": source,
        "uploaded_at": timestamp,
        "files": filenames,
    }
    if provenance is not None:
        entry["user_turns"] = provenance.user_turns
        entry["duration_minutes"] = provenance.duration_minutes
        entry["raw_size_kb"] = provenance.raw_size_kb
    entry["xml_size_kb"] = xml_size_kb
    entry["git_branch"] = git_branch
    return entry


def _update_manifest(
    *,
    existing_manifest: dict | None,
    plan_id: int,
    new_entry: dict,
) -> dict:
    """Update manifest with a new session entry (idempotent).

    If the session_id already exists, removes the old entry before appending.
    """
    if existing_manifest is None:
        manifest: dict = {
            "version": 1,
            "plan_id": plan_id,
            "sessions": [],
        }
    else:
        manifest = dict(existing_manifest)

    sessions = list(manifest.get("sessions", []))
    # Remove existing entry with same session_id (idempotency)
    sessions = [s for s in sessions if s.get("session_id") != new_entry["session_id"]]
    sessions.append(new_entry)
    manifest["sessions"] = sessions
    return manifest


@click.command(name="push-session")
@click.option(
    "--session-file",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the session JSONL file to preprocess and upload",
)
@click.option(
    "--session-id",
    required=True,
    help="Claude Code session ID",
)
@click.option(
    "--stage",
    required=True,
    type=click.Choice(["planning", "impl", "address"]),
    help="Lifecycle stage: planning, impl, or address",
)
@click.option(
    "--source",
    required=True,
    type=click.Choice(["local", "remote"]),
    help="Session source: 'local' or 'remote'",
)
@click.option(
    "--plan-id",
    required=True,
    type=int,
    help="Plan identifier for the planned-pr-context branch",
)
@click.pass_context
def push_session(
    ctx: click.Context,
    session_file: Path,
    session_id: str,
    stage: Literal["planning", "impl", "address"],
    source: Literal["local", "remote"],
    plan_id: int,
) -> None:
    """Preprocess and push a session to the planned-pr-context branch with accumulation.

    Preprocesses the session JSONL to compressed XML, then pushes the XML files
    to the planned-pr-context/{plan_id} branch, accumulating across lifecycle stages.
    Updates the manifest and plan metadata.

    Always exits with code 0 (non-critical operation).
    """
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    time = require_time(ctx)

    # Step 0: Compute provenance stats from raw JSONL (before preprocessing)
    provenance = _compute_session_provenance(session_file)

    # Step 1: Preprocess session to XML
    xml_files = _preprocess_session(
        session_file=session_file,
        stage=stage,
        session_id=session_id,
        repo_root=repo_root,
    )

    if xml_files is None:
        click.echo(json.dumps({"uploaded": False, "reason": "preprocessing_failed"}))
        return

    # Compute XML size from generated files
    xml_size_kb = sum(f.stat().st_size for f in xml_files) // 1024

    # Get the current git branch for provenance
    git_branch = git.branch.get_current_branch(repo_root)

    session_branch = f"planned-pr-context/{plan_id}"
    timestamp = time.now().replace(tzinfo=UTC).isoformat()

    # Step 2: Fetch or create branch
    if git.branch.branch_exists_on_remote(repo_root, "origin", session_branch):
        # Fetch remote state and create local branch tracking it
        git.remote.fetch_branch(repo_root, "origin", session_branch)
        git.branch.delete_branch(repo_root, session_branch, force=True)
        git.branch.create_branch(repo_root, session_branch, f"origin/{session_branch}", force=False)
        # Read existing manifest
        existing_manifest = _read_manifest_from_branch(
            repo_root=repo_root,
            session_branch=session_branch,
            git=git,
        )
    else:
        # First upload — create from origin/master
        git.branch.delete_branch(repo_root, session_branch, force=True)
        git.branch.create_branch(repo_root, session_branch, "origin/master", force=False)
        existing_manifest = None

    # Step 3: Build file map for commit
    filenames: list[str] = []
    files_to_commit: dict[str, str] = {}
    for xml_file in xml_files:
        filename = xml_file.name
        filenames.append(filename)
        files_to_commit[f".erk/sessions/{filename}"] = xml_file.read_text(encoding="utf-8")

    # Step 4: Build and add manifest
    manifest_entry = _build_manifest_entry(
        session_id=session_id,
        stage=stage,
        source=source,
        timestamp=timestamp,
        filenames=filenames,
        provenance=provenance,
        xml_size_kb=xml_size_kb,
        git_branch=git_branch,
    )
    manifest = _update_manifest(
        existing_manifest=existing_manifest,
        plan_id=plan_id,
        new_entry=manifest_entry,
    )
    files_to_commit[".erk/sessions/manifest.json"] = json.dumps(manifest, indent=2)

    # Step 5: Commit files to branch
    git.commit.commit_files_to_branch(
        repo_root,
        branch=session_branch,
        files=files_to_commit,
        message=f"Push {stage} session {session_id} for plan #{plan_id}",
    )

    # Step 6: Force-push
    git.remote.push_to_remote(repo_root, "origin", session_branch, set_upstream=True, force=True)

    # Step 7: Update plan metadata
    backend = require_plan_backend(ctx)
    plan_id_str = str(plan_id)
    metadata: dict[str, object] = {
        "last_session_branch": session_branch,
        "last_session_id": session_id,
        "last_session_at": timestamp,
        "last_session_source": source,
    }

    plan_result = backend.get_plan(repo_root, plan_id_str)
    if not isinstance(plan_result, PlanNotFound):
        try:
            backend.update_metadata(repo_root, plan_id_str, metadata)
        except RuntimeError:
            pass  # Non-critical: session branch was still created

    # Step 8: Clean up scratch files
    scratch_dir = repo_root / ".erk" / "scratch" / "push-session"
    if scratch_dir.exists():
        for f in scratch_dir.iterdir():
            if f.is_file():
                f.unlink()

    result_output: dict[str, object] = {
        "uploaded": True,
        "plan_id": plan_id,
        "session_branch": session_branch,
        "session_id": session_id,
        "stage": stage,
        "files": filenames,
    }
    click.echo(json.dumps(result_output))
