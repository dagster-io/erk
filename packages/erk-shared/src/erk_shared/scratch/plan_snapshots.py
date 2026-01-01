"""Plan snapshot utilities for session-scoped plan archival.

Creates durable archives of Claude Code plan files in the session scratch directory.
This compensates for Claude Code's opaque plan file naming and overwrite behavior.

Storage layout:
    .erk/scratch/sessions/<session-id>/plans/
        000001-a1b2c3d4/
            quirky-drifting-comet.md        # Original Claude filename preserved
            quirky-drifting-comet.meta.json # Provenance metadata
        000002-e5f6g7h8/
            bold-flying-star.md
            bold-flying-star.meta.json
"""

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.extraction.local_plans import (
    extract_planning_agent_ids,
    extract_slugs_from_session,
)
from erk_shared.scratch.scratch import get_scratch_dir


@dataclass(frozen=True)
class PlanSnapshotMetadata:
    """Metadata sidecar for a plan snapshot."""

    slug: str
    captured_at: str
    content_hash: str
    source_path: str
    planning_agent_ids: list[str]


@dataclass(frozen=True)
class PlanSnapshot:
    """Result of creating a plan snapshot."""

    snapshot_dir: Path
    plan_file: Path
    metadata_file: Path
    sequence_number: int
    content_hash_short: str


# ============================================================================
# Pure Functions
# ============================================================================


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content with 'sha256:' prefix.

    Args:
        content: The string content to hash.

    Returns:
        Hash string in format 'sha256:<hex>'.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def extract_short_hash(full_hash: str) -> str:
    """Extract first 8 characters after the prefix from a full hash.

    Args:
        full_hash: Hash in format 'sha256:<hex>'.

    Returns:
        First 8 characters of the hex portion.
    """
    # Skip "sha256:" prefix (7 chars) and take first 8 chars
    return full_hash[7:15]


def build_snapshot_folder_name(sequence: int, hash_short: str) -> str:
    """Build snapshot folder name from sequence and short hash.

    Args:
        sequence: Sequence number (1-based).
        hash_short: First 8 characters of content hash.

    Returns:
        Folder name in format '000001-a1b2c3d4'.
    """
    return f"{sequence:06d}-{hash_short}"


def determine_next_sequence(existing_folders: list[str]) -> int:
    """Determine next sequence number from existing folder names.

    Args:
        existing_folders: List of existing folder names.

    Returns:
        Next sequence number (1 if empty, max+1 otherwise).
    """
    if not existing_folders:
        return 1

    max_sequence = 0
    for folder in existing_folders:
        # Parse "000001-a1b2c3d4" format
        if "-" in folder:
            sequence_str = folder.split("-")[0]
            # Only parse if it looks like a valid sequence number
            if sequence_str.isdigit():
                sequence = int(sequence_str)
                if sequence > max_sequence:
                    max_sequence = sequence

    return max_sequence + 1


# ============================================================================
# I/O Functions
# ============================================================================


def get_plans_snapshot_dir(session_id: str, *, repo_root: Path | None) -> Path:
    """Get the plans snapshot directory for a session.

    Args:
        session_id: Claude session ID.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        Path to .erk/scratch/sessions/<session-id>/plans/ directory.
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    return scratch_dir / "plans"


def snapshot_plan_file(
    session_id: str,
    plan_file_path: Path,
    slug: str,
    planning_agent_ids: list[str],
    *,
    repo_root: Path | None = None,
) -> PlanSnapshot:
    """Snapshot a plan file to permanent session-scoped storage.

    Creates a snapshot directory with the plan file and metadata sidecar.

    Args:
        session_id: Claude session ID.
        plan_file_path: Path to the plan file to snapshot.
        slug: The plan slug (Claude's filename without extension).
        planning_agent_ids: List of agent IDs that contributed to the plan.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        PlanSnapshot with paths to created files.
    """
    plans_dir = get_plans_snapshot_dir(session_id, repo_root=repo_root)
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Read content and compute hash
    content = plan_file_path.read_text(encoding="utf-8")
    content_hash = compute_content_hash(content)
    hash_short = extract_short_hash(content_hash)

    # Determine sequence number
    existing_folders = [d.name for d in plans_dir.iterdir() if d.is_dir()]
    sequence = determine_next_sequence(existing_folders)

    # Create snapshot directory
    folder_name = build_snapshot_folder_name(sequence, hash_short)
    snapshot_dir = plans_dir / folder_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Copy plan file (preserve original filename)
    dest_plan_file = snapshot_dir / plan_file_path.name
    shutil.copy2(plan_file_path, dest_plan_file)

    # Write metadata
    metadata = PlanSnapshotMetadata(
        slug=slug,
        captured_at=datetime.now(UTC).isoformat(),
        content_hash=content_hash,
        source_path=str(plan_file_path),
        planning_agent_ids=list(planning_agent_ids),
    )
    metadata_file = snapshot_dir / f"{slug}.meta.json"
    metadata_dict = {
        "slug": metadata.slug,
        "captured_at": metadata.captured_at,
        "content_hash": metadata.content_hash,
        "source_path": metadata.source_path,
        "planning_agent_ids": metadata.planning_agent_ids,
    }
    metadata_file.write_text(json.dumps(metadata_dict, indent=2), encoding="utf-8")

    return PlanSnapshot(
        snapshot_dir=snapshot_dir,
        plan_file=dest_plan_file,
        metadata_file=metadata_file,
        sequence_number=sequence,
        content_hash_short=hash_short,
    )


def snapshot_plan_for_session(
    session_id: str,
    plan_file_path: Path,
    cwd_hint: str,
    *,
    repo_root: Path | None = None,
) -> PlanSnapshot:
    """Snapshot a plan file with session context auto-discovery.

    Convenience function that extracts the slug and planning agent IDs
    from session logs, then calls snapshot_plan_file.

    Args:
        session_id: Claude session ID.
        plan_file_path: Path to the plan file to snapshot.
        cwd_hint: Current working directory hint for session lookup.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        PlanSnapshot with paths to created files.
    """
    slugs = extract_slugs_from_session(session_id, cwd_hint=cwd_hint)
    slug = slugs[-1] if slugs else "unknown"

    planning_agent_ids = extract_planning_agent_ids(session_id, cwd_hint=cwd_hint)

    return snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file_path,
        slug=slug,
        planning_agent_ids=planning_agent_ids,
        repo_root=repo_root,
    )
