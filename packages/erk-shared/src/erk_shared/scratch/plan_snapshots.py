"""Plan snapshot utilities for session-scoped plan archival.

Creates durable archives of Claude Code plan files in the session scratch directory.
This compensates for Claude Code's opaque plan file naming and overwrite behavior.

Storage layout:
    .erk/scratch/sessions/<session-id>/plan_snapshots/
        000001-a1b2c3d4/
            quirky-drifting-comet.md        # Plan content with YAML frontmatter metadata
        000002-e5f6g7h8/
            bold-flying-star.md
"""

import hashlib
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.gateway.claude_installation.abc import ClaudeInstallation
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
    """Immutable archive of a plan file captured at save time.

    Plans in ~/.claude/plans/ are mutable — Claude overwrites them during a session.
    When a plan is saved to GitHub (as an issue or draft PR), a snapshot preserves
    the exact content that was shipped, stored in session-scoped scratch storage
    (.erk/scratch/{session_id}/plan_snapshots/). This serves two purposes:

    1. Audit trail: the snapshot is the authoritative record of what was saved,
       even if the source plan file is later modified or deleted.
    2. Deduplication: marker files reference the snapshot to detect if a session
       already saved a plan, preventing duplicate GitHub issues/PRs.

    The snapshot is a single .md file with YAML frontmatter containing provenance
    metadata (slug, content hash, source path, planning agent IDs).
    """

    snapshot_dir: Path
    plan_file: Path
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
    """Get the plan snapshots directory for a session.

    Args:
        session_id: Claude session ID.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        Path to .erk/scratch/sessions/<session-id>/plan_snapshots/ directory.
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    return scratch_dir / "plan_snapshots"


def _format_frontmatter(metadata: PlanSnapshotMetadata) -> str:
    """Format metadata as YAML frontmatter string.

    Args:
        metadata: Snapshot metadata to format.

    Returns:
        YAML frontmatter block including --- delimiters and trailing newline.
    """
    lines = [
        "---",
        f"slug: {metadata.slug}",
        f"captured_at: '{metadata.captured_at}'",
        f"content_hash: '{metadata.content_hash}'",
        f"source_path: '{metadata.source_path}'",
        "planning_agent_ids:",
    ]
    for agent_id in metadata.planning_agent_ids:
        lines.append(f"- {agent_id}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def snapshot_plan_file(
    session_id: str,
    plan_file_path: Path,
    slug: str,
    planning_agent_ids: list[str],
    *,
    repo_root: Path | None = None,
) -> PlanSnapshot:
    """Snapshot a plan file to permanent session-scoped storage.

    Creates a snapshot directory with a single .md file containing the plan
    content prefixed with YAML frontmatter metadata.

    Args:
        session_id: Claude session ID.
        plan_file_path: Path to the plan file to snapshot.
        slug: The plan slug (Claude's filename without extension).
        planning_agent_ids: List of agent IDs that contributed to the plan.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        PlanSnapshot with path to the created file.
    """
    plans_dir = get_plans_snapshot_dir(session_id, repo_root=repo_root)
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Read content and compute hash (hash the original content, not with frontmatter)
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

    # Build metadata frontmatter
    metadata = PlanSnapshotMetadata(
        slug=slug,
        captured_at=datetime.now(UTC).isoformat(),
        content_hash=content_hash,
        source_path=str(plan_file_path),
        planning_agent_ids=list(planning_agent_ids),
    )
    frontmatter = _format_frontmatter(metadata)

    # Write plan file with frontmatter prepended
    dest_plan_file = snapshot_dir / plan_file_path.name
    dest_plan_file.write_text(frontmatter + content, encoding="utf-8")

    return PlanSnapshot(
        snapshot_dir=snapshot_dir,
        plan_file=dest_plan_file,
        sequence_number=sequence,
        content_hash_short=hash_short,
    )


def snapshot_plan_for_session(
    session_id: str,
    plan_file_path: Path,
    project_cwd: Path,
    claude_installation: ClaudeInstallation,
    *,
    repo_root: Path | None,
) -> PlanSnapshot:
    """Snapshot a plan file with session context auto-discovery.

    Convenience function that extracts the slug and planning agent IDs
    from session logs via the gateway, then calls snapshot_plan_file.

    Args:
        session_id: Claude session ID.
        plan_file_path: Path to the plan file to snapshot.
        project_cwd: Project working directory for session lookup.
        claude_installation: Gateway to Claude installation data.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        PlanSnapshot with paths to created files.
    """
    slugs = claude_installation.extract_slugs_from_session(project_cwd, session_id)
    slug = slugs[-1] if slugs else "unknown"

    planning_agent_ids = claude_installation.extract_planning_agent_ids(project_cwd, session_id)

    return snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file_path,
        slug=slug,
        planning_agent_ids=planning_agent_ids,
        repo_root=repo_root,
    )
