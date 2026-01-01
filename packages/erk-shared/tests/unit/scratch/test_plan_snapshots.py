"""Unit tests for plan_snapshots module."""

import json
from pathlib import Path

from erk_shared.scratch.plan_snapshots import (
    build_snapshot_folder_name,
    compute_content_hash,
    determine_next_sequence,
    extract_short_hash,
    get_plans_snapshot_dir,
    snapshot_plan_file,
)

# compute_content_hash tests


def test_compute_content_hash_returns_sha256_format() -> None:
    """Verify hash is returned with sha256: prefix."""
    content = "test content"

    result = compute_content_hash(content)

    assert result.startswith("sha256:")
    # SHA256 hex is 64 chars, plus 7 for "sha256:" prefix = 71 total
    assert len(result) == 71


def test_compute_content_hash_deterministic() -> None:
    """Verify same content always produces same hash."""
    content = "test content"

    result1 = compute_content_hash(content)
    result2 = compute_content_hash(content)

    assert result1 == result2


def test_compute_content_hash_different_content_different_hash() -> None:
    """Verify different content produces different hashes."""
    result1 = compute_content_hash("content 1")
    result2 = compute_content_hash("content 2")

    assert result1 != result2


# extract_short_hash tests


def test_extract_short_hash_extracts_first_8_chars() -> None:
    """Verify first 8 characters after prefix are extracted."""
    full_hash = "sha256:a1b2c3d4e5f6g7h8i9j0"

    result = extract_short_hash(full_hash)

    assert result == "a1b2c3d4"
    assert len(result) == 8


# build_snapshot_folder_name tests


def test_build_snapshot_folder_name_zero_pads() -> None:
    """Verify sequence is zero-padded to 6 digits."""
    result = build_snapshot_folder_name(1, "a1b2c3d4")

    assert result == "000001-a1b2c3d4"


def test_build_snapshot_folder_name_large_sequence() -> None:
    """Verify larger sequence numbers are formatted correctly."""
    result = build_snapshot_folder_name(12345, "e5f6g7h8")

    assert result == "012345-e5f6g7h8"


# determine_next_sequence tests


def test_determine_next_sequence_empty_returns_one() -> None:
    """Verify empty list returns 1."""
    result = determine_next_sequence([])

    assert result == 1


def test_determine_next_sequence_increments() -> None:
    """Verify returns max sequence + 1."""
    existing = ["000001-abc12345", "000002-def67890", "000003-ghi11111"]

    result = determine_next_sequence(existing)

    assert result == 4


def test_determine_next_sequence_handles_gaps() -> None:
    """Verify handles non-contiguous sequences correctly."""
    existing = ["000001-abc12345", "000005-def67890"]

    result = determine_next_sequence(existing)

    assert result == 6


def test_determine_next_sequence_ignores_malformed() -> None:
    """Verify ignores folders without the expected format."""
    existing = ["000001-abc12345", "not-a-sequence"]

    result = determine_next_sequence(existing)

    assert result == 2


# get_plans_snapshot_dir tests


def test_get_plans_snapshot_dir_returns_correct_path(tmp_path: Path) -> None:
    """Verify returns correct plans subdirectory path."""
    session_id = "test-session-123"

    result = get_plans_snapshot_dir(session_id, repo_root=tmp_path)

    expected = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "plans"
    assert result == expected


# snapshot_plan_file tests


def test_snapshot_plan_file_creates_structure(tmp_path: Path) -> None:
    """Verify snapshot creates directory structure."""
    session_id = "test-session-123"
    plan_file = tmp_path / "source-plan.md"
    plan_file.write_text("# Plan Content", encoding="utf-8")

    result = snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file,
        slug="test-slug",
        planning_agent_ids=["agent-abc123"],
        repo_root=tmp_path,
    )

    assert result.snapshot_dir.exists()
    assert result.snapshot_dir.is_dir()


def test_snapshot_plan_file_preserves_filename(tmp_path: Path) -> None:
    """Verify original plan filename is preserved."""
    session_id = "test-session-123"
    plan_file = tmp_path / "quirky-drifting-comet.md"
    plan_file.write_text("# Plan Content", encoding="utf-8")

    result = snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file,
        slug="quirky-drifting-comet",
        planning_agent_ids=[],
        repo_root=tmp_path,
    )

    assert result.plan_file.name == "quirky-drifting-comet.md"
    assert result.plan_file.exists()
    assert result.plan_file.read_text(encoding="utf-8") == "# Plan Content"


def test_snapshot_plan_file_writes_metadata(tmp_path: Path) -> None:
    """Verify metadata file is written with correct content."""
    session_id = "test-session-123"
    plan_file = tmp_path / "test-plan.md"
    plan_content = "# My Plan"
    plan_file.write_text(plan_content, encoding="utf-8")

    result = snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file,
        slug="test-slug",
        planning_agent_ids=["agent-abc123", "agent-def456"],
        repo_root=tmp_path,
    )

    assert result.metadata_file.exists()
    assert result.metadata_file.name == "test-slug.meta.json"
    metadata = json.loads(result.metadata_file.read_text(encoding="utf-8"))

    assert metadata["slug"] == "test-slug"
    assert metadata["source_path"] == str(plan_file)
    assert metadata["planning_agent_ids"] == ["agent-abc123", "agent-def456"]
    assert metadata["content_hash"].startswith("sha256:")
    assert "captured_at" in metadata


def test_snapshot_plan_file_increments_sequence(tmp_path: Path) -> None:
    """Verify sequence number increments with each snapshot."""
    session_id = "test-session-123"
    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text("# Plan 1", encoding="utf-8")

    result1 = snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file,
        slug="test-slug",
        planning_agent_ids=[],
        repo_root=tmp_path,
    )

    # Modify content for different hash
    plan_file.write_text("# Plan 2", encoding="utf-8")

    result2 = snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file,
        slug="test-slug",
        planning_agent_ids=[],
        repo_root=tmp_path,
    )

    assert result1.sequence_number == 1
    assert result2.sequence_number == 2
    assert result1.snapshot_dir != result2.snapshot_dir


def test_snapshot_plan_file_hash_in_folder_name(tmp_path: Path) -> None:
    """Verify folder name contains content hash."""
    session_id = "test-session-123"
    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text("# Specific Content", encoding="utf-8")

    result = snapshot_plan_file(
        session_id=session_id,
        plan_file_path=plan_file,
        slug="test-slug",
        planning_agent_ids=[],
        repo_root=tmp_path,
    )

    folder_name = result.snapshot_dir.name
    assert folder_name.startswith("000001-")
    assert result.content_hash_short in folder_name
