"""Unit tests for hook logging functions.

Tests the clear_hook_logs function that removes hook execution logs.
"""

from pathlib import Path

from erk_shared.hooks.logging import clear_hook_logs


def test_clear_hook_logs_removes_json_files(tmp_path: Path) -> None:
    """Test that clear_hook_logs removes all JSON log files."""
    # Arrange: Create hook log files
    session_dir = tmp_path / ".erk" / "scratch" / "sessions" / "test-session"
    hook_dir = session_dir / "hooks" / "my-hook"
    hook_dir.mkdir(parents=True)

    log1 = hook_dir / "2025-01-05T10-00-00.json"
    log2 = hook_dir / "2025-01-05T11-00-00.json"
    log1.write_text('{"test": 1}', encoding="utf-8")
    log2.write_text('{"test": 2}', encoding="utf-8")

    # Act
    deleted_count = clear_hook_logs(tmp_path)

    # Assert
    assert deleted_count == 2
    assert not log1.exists()
    assert not log2.exists()


def test_clear_hook_logs_returns_correct_count(tmp_path: Path) -> None:
    """Test that clear_hook_logs returns the correct count of deleted files."""
    # Arrange: Create multiple sessions with multiple hooks
    for session_id in ["session-1", "session-2"]:
        for hook_id in ["hook-a", "hook-b"]:
            hook_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "hooks" / hook_id
            hook_dir.mkdir(parents=True)
            (hook_dir / "log1.json").write_text("{}", encoding="utf-8")
            (hook_dir / "log2.json").write_text("{}", encoding="utf-8")

    # Act
    deleted_count = clear_hook_logs(tmp_path)

    # Assert: 2 sessions * 2 hooks * 2 logs = 8 files
    assert deleted_count == 8


def test_clear_hook_logs_removes_empty_directories(tmp_path: Path) -> None:
    """Test that clear_hook_logs removes empty hook directories after clearing."""
    # Arrange
    session_dir = tmp_path / ".erk" / "scratch" / "sessions" / "test-session"
    hook_dir = session_dir / "hooks" / "my-hook"
    hook_dir.mkdir(parents=True)
    log_file = hook_dir / "test.json"
    log_file.write_text('{"test": 1}', encoding="utf-8")

    # Act
    clear_hook_logs(tmp_path)

    # Assert: Hook directory should be removed (was empty after clearing)
    assert not hook_dir.exists()
    # Hooks directory should also be removed
    assert not (session_dir / "hooks").exists()


def test_clear_hook_logs_with_no_logs_returns_zero(tmp_path: Path) -> None:
    """Test that clear_hook_logs returns 0 when no logs exist."""
    # Arrange: Create empty session structure
    session_dir = tmp_path / ".erk" / "scratch" / "sessions" / "test-session"
    hooks_dir = session_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    # Act
    deleted_count = clear_hook_logs(tmp_path)

    # Assert
    assert deleted_count == 0


def test_clear_hook_logs_with_no_sessions_dir_returns_zero(tmp_path: Path) -> None:
    """Test that clear_hook_logs returns 0 when sessions directory doesn't exist."""
    # Arrange: Create no sessions directory
    (tmp_path / ".erk" / "scratch").mkdir(parents=True)

    # Act
    deleted_count = clear_hook_logs(tmp_path)

    # Assert
    assert deleted_count == 0


def test_clear_hook_logs_preserves_other_files(tmp_path: Path) -> None:
    """Test that clear_hook_logs only removes JSON files in hooks directories."""
    # Arrange
    session_dir = tmp_path / ".erk" / "scratch" / "sessions" / "test-session"
    hook_dir = session_dir / "hooks" / "my-hook"
    hook_dir.mkdir(parents=True)

    # JSON log file (should be deleted)
    json_log = hook_dir / "test.json"
    json_log.write_text("{}", encoding="utf-8")

    # Other file in hook directory (should be preserved)
    other_file = hook_dir / "other.txt"
    other_file.write_text("keep me", encoding="utf-8")

    # File in session directory (should be preserved)
    session_file = session_dir / "session-data.json"
    session_file.write_text("{}", encoding="utf-8")

    # Act
    deleted_count = clear_hook_logs(tmp_path)

    # Assert
    assert deleted_count == 1
    assert not json_log.exists()
    assert other_file.exists()
    assert session_file.exists()


def test_clear_hook_logs_preserves_non_empty_hook_directories(tmp_path: Path) -> None:
    """Test that hook directories with non-JSON files are not removed."""
    # Arrange
    session_dir = tmp_path / ".erk" / "scratch" / "sessions" / "test-session"
    hook_dir = session_dir / "hooks" / "my-hook"
    hook_dir.mkdir(parents=True)

    # JSON log file (should be deleted)
    json_log = hook_dir / "test.json"
    json_log.write_text("{}", encoding="utf-8")

    # Other file that keeps the directory from being empty
    other_file = hook_dir / "keep.txt"
    other_file.write_text("keep", encoding="utf-8")

    # Act
    clear_hook_logs(tmp_path)

    # Assert: Directory should still exist because it has non-JSON file
    assert hook_dir.exists()
    assert other_file.exists()
