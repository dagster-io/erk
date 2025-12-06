"""Unit tests for scratch module."""

import os
import time
from pathlib import Path

from erk_shared.scratch.scratch import (
    cleanup_stale_scratch,
    get_scratch_dir,
    write_scratch_file,
)

# get_scratch_dir tests


def test_get_scratch_dir_creates_directory(tmp_path: Path) -> None:
    """Verify .erk/scratch/sessions/<session_id>/ is created."""
    session_id = "test-session-123"

    result = get_scratch_dir(session_id, repo_root=tmp_path)

    assert result == tmp_path / ".erk" / "scratch" / "sessions" / session_id
    assert result.exists()
    assert result.is_dir()


def test_get_scratch_dir_idempotent(tmp_path: Path) -> None:
    """Verify calling multiple times returns same path."""
    session_id = "test-session-123"

    result1 = get_scratch_dir(session_id, repo_root=tmp_path)
    result2 = get_scratch_dir(session_id, repo_root=tmp_path)

    assert result1 == result2
    assert result1.exists()


def test_get_scratch_dir_different_sessions(tmp_path: Path) -> None:
    """Verify different session IDs get different directories."""
    result1 = get_scratch_dir("session-1", repo_root=tmp_path)
    result2 = get_scratch_dir("session-2", repo_root=tmp_path)

    assert result1 != result2
    assert result1.exists()
    assert result2.exists()


# write_scratch_file tests


def test_write_scratch_file_creates_unique_files(tmp_path: Path) -> None:
    """Verify unique naming pattern generates different files."""
    session_id = "test-session-123"
    content = "test content"

    path1 = write_scratch_file(content, session_id=session_id, repo_root=tmp_path)
    path2 = write_scratch_file(content, session_id=session_id, repo_root=tmp_path)

    assert path1 != path2
    assert path1.exists()
    assert path2.exists()


def test_write_scratch_file_content(tmp_path: Path) -> None:
    """Verify content is written correctly."""
    session_id = "test-session-123"
    content = "line 1\nline 2\nline 3"

    path = write_scratch_file(content, session_id=session_id, repo_root=tmp_path)

    assert path.read_text(encoding="utf-8") == content


def test_write_scratch_file_uses_suffix(tmp_path: Path) -> None:
    """Verify suffix parameter sets file extension."""
    session_id = "test-session-123"

    path = write_scratch_file("content", session_id=session_id, suffix=".diff", repo_root=tmp_path)

    assert path.suffix == ".diff"


def test_write_scratch_file_uses_prefix(tmp_path: Path) -> None:
    """Verify prefix parameter sets filename prefix."""
    session_id = "test-session-123"

    path = write_scratch_file(
        "content", session_id=session_id, prefix="pr-diff-", repo_root=tmp_path
    )

    assert path.name.startswith("pr-diff-")


def test_write_scratch_file_in_session_directory(tmp_path: Path) -> None:
    """Verify file is created in .erk/scratch/sessions/<session_id>/ directory."""
    session_id = "test-session-123"

    path = write_scratch_file("content", session_id=session_id, repo_root=tmp_path)

    expected_parent = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    assert path.parent == expected_parent


# cleanup_stale_scratch tests


def test_cleanup_stale_scratch_removes_old_directories(tmp_path: Path) -> None:
    """Verify old session directories are removed."""
    old_session = tmp_path / ".erk" / "scratch" / "sessions" / "old-session"
    old_session.mkdir(parents=True)
    old_file = old_session / "test.txt"
    old_file.write_text("old content", encoding="utf-8")

    # Set mtime to 2 hours ago
    old_mtime = time.time() - 7200
    os.utime(old_session, (old_mtime, old_mtime))

    cleaned = cleanup_stale_scratch(max_age_seconds=3600, repo_root=tmp_path)

    assert cleaned == 1
    assert not old_session.exists()


def test_cleanup_stale_scratch_preserves_new_directories(tmp_path: Path) -> None:
    """Verify recent session directories are not removed."""
    new_session = tmp_path / ".erk" / "scratch" / "sessions" / "new-session"
    new_session.mkdir(parents=True)
    new_file = new_session / "test.txt"
    new_file.write_text("new content", encoding="utf-8")

    cleaned = cleanup_stale_scratch(max_age_seconds=3600, repo_root=tmp_path)

    assert cleaned == 0
    assert new_session.exists()
    assert new_file.exists()


def test_cleanup_stale_scratch_returns_zero_when_no_tmp_dir(tmp_path: Path) -> None:
    """Verify returns 0 when .erk/scratch/ doesn't exist."""
    cleaned = cleanup_stale_scratch(repo_root=tmp_path)

    assert cleaned == 0


def test_cleanup_stale_scratch_handles_mixed_age_directories(tmp_path: Path) -> None:
    """Verify only old directories are removed, not new ones."""
    sessions_dir = tmp_path / ".erk" / "scratch" / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create old session
    old_session = sessions_dir / "old-session"
    old_session.mkdir()
    (old_session / "file.txt").write_text("old", encoding="utf-8")
    old_mtime = time.time() - 7200
    os.utime(old_session, (old_mtime, old_mtime))

    # Create new session
    new_session = sessions_dir / "new-session"
    new_session.mkdir()
    (new_session / "file.txt").write_text("new", encoding="utf-8")

    cleaned = cleanup_stale_scratch(max_age_seconds=3600, repo_root=tmp_path)

    assert cleaned == 1
    assert not old_session.exists()
    assert new_session.exists()


def test_cleanup_stale_scratch_ignores_files_in_sessions_dir(tmp_path: Path) -> None:
    """Verify files directly in .erk/scratch/sessions/ are ignored (only directories cleaned)."""
    sessions_dir = tmp_path / ".erk" / "scratch" / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create a file directly in .erk/scratch/sessions/
    direct_file = sessions_dir / "direct-file.txt"
    direct_file.write_text("content", encoding="utf-8")

    # Make it old
    old_mtime = time.time() - 7200
    os.utime(direct_file, (old_mtime, old_mtime))

    # Cleanup should not remove files
    cleaned = cleanup_stale_scratch(max_age_seconds=3600, repo_root=tmp_path)

    assert cleaned == 0
    assert direct_file.exists()
