"""Tests for hook logging I/O functions."""

import json
from pathlib import Path

from erk_shared.hooks.logging import (
    get_hook_log_dir,
    read_hook_log,
    read_recent_hook_logs,
    truncate_string,
    write_hook_log,
)
from erk_shared.hooks.types import HookExecutionLog, HookExitStatus


class TestGetHookLogDir:
    """Tests for get_hook_log_dir function."""

    def test_returns_correct_path_with_repo_root(self, tmp_path: Path) -> None:
        result = get_hook_log_dir("session-123", "my-hook", repo_root=tmp_path)
        expected = tmp_path / ".erk" / "scratch" / "sessions" / "session-123" / "hooks" / "my-hook"
        assert result == expected


class TestWriteHookLog:
    """Tests for write_hook_log function."""

    def test_writes_log_file(self, tmp_path: Path) -> None:
        log = HookExecutionLog(
            kit_id="test-kit",
            hook_id="test-hook",
            session_id="session-abc",
            started_at="2024-01-01T12:00:00+00:00",
            ended_at="2024-01-01T12:00:01+00:00",
            duration_ms=1000,
            exit_code=0,
            exit_status=HookExitStatus.SUCCESS,
            stdout="hello",
            stderr="",
            stdin_context='{"session_id": "session-abc"}',
        )

        result_path = write_hook_log(log, repo_root=tmp_path)

        assert result_path is not None
        assert result_path.exists()
        content = json.loads(result_path.read_text(encoding="utf-8"))
        assert content["kit_id"] == "test-kit"
        assert content["hook_id"] == "test-hook"
        assert content["exit_status"] == "success"

    def test_returns_none_when_no_session_id(self, tmp_path: Path) -> None:
        log = HookExecutionLog(
            kit_id="test-kit",
            hook_id="test-hook",
            session_id=None,  # No session ID
            started_at="2024-01-01T12:00:00+00:00",
            ended_at="2024-01-01T12:00:01+00:00",
            duration_ms=1000,
            exit_code=0,
            exit_status=HookExitStatus.SUCCESS,
            stdout="",
            stderr="",
            stdin_context="",
        )

        result_path = write_hook_log(log, repo_root=tmp_path)
        assert result_path is None


class TestReadHookLog:
    """Tests for read_hook_log function."""

    def test_reads_written_log(self, tmp_path: Path) -> None:
        log = HookExecutionLog(
            kit_id="test-kit",
            hook_id="test-hook",
            session_id="session-xyz",
            started_at="2024-01-01T12:00:00+00:00",
            ended_at="2024-01-01T12:00:01+00:00",
            duration_ms=1000,
            exit_code=1,
            exit_status=HookExitStatus.ERROR,
            stdout="output",
            stderr="error message",
            stdin_context="{}",
            error_message="Something went wrong",
        )

        result_path = write_hook_log(log, repo_root=tmp_path)
        assert result_path is not None

        read_log = read_hook_log(result_path)

        assert read_log is not None
        assert read_log.kit_id == "test-kit"
        assert read_log.hook_id == "test-hook"
        assert read_log.exit_status == HookExitStatus.ERROR
        assert read_log.error_message == "Something went wrong"

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path) -> None:
        result = read_hook_log(tmp_path / "nonexistent.json")
        assert result is None


class TestReadRecentHookLogs:
    """Tests for read_recent_hook_logs function."""

    def test_returns_empty_when_no_sessions_dir(self, tmp_path: Path) -> None:
        result = read_recent_hook_logs(tmp_path)
        assert result == []

    def test_reads_logs_from_multiple_sessions(self, tmp_path: Path) -> None:
        # Write logs to two different sessions
        log1 = HookExecutionLog(
            kit_id="kit1",
            hook_id="hook1",
            session_id="session-1",
            started_at="2024-01-01T12:00:00+00:00",
            ended_at="2024-01-01T12:00:01+00:00",
            duration_ms=1000,
            exit_code=0,
            exit_status=HookExitStatus.SUCCESS,
            stdout="",
            stderr="",
            stdin_context="",
        )
        log2 = HookExecutionLog(
            kit_id="kit2",
            hook_id="hook2",
            session_id="session-2",
            started_at="2024-01-01T12:01:00+00:00",
            ended_at="2024-01-01T12:01:01+00:00",
            duration_ms=1000,
            exit_code=2,
            exit_status=HookExitStatus.BLOCKED,
            stdout="",
            stderr="",
            stdin_context="",
        )

        write_hook_log(log1, repo_root=tmp_path)
        write_hook_log(log2, repo_root=tmp_path)

        result = read_recent_hook_logs(tmp_path)

        assert len(result) == 2
        # Should be sorted by started_at descending (newest first)
        assert result[0].hook_id == "hook2"
        assert result[1].hook_id == "hook1"


class TestTruncateString:
    """Tests for truncate_string function."""

    def test_short_string_unchanged(self) -> None:
        result = truncate_string("hello", max_bytes=100)
        assert result == "hello"

    def test_truncates_long_string(self) -> None:
        result = truncate_string("a" * 200, max_bytes=50)
        assert len(result.encode("utf-8")) <= 50
        assert result.endswith("[truncated]")

    def test_handles_unicode_correctly(self) -> None:
        # Unicode characters can be multi-byte
        result = truncate_string("emoji" * 20, max_bytes=30)
        # Should not raise and should be valid UTF-8
        result.encode("utf-8")
