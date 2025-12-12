"""Tests for check_hook_health health check.

These tests verify the health check correctly reports hook execution status
from logs written by the @logged_hook decorator.
"""

import json
from pathlib import Path

from erk.core.health_checks import check_hook_health


def _write_hook_log(
    repo_root: Path,
    session_id: str,
    hook_id: str,
    exit_status: str,
    exit_code: int,
    timestamp: str,
    error_message: str | None = None,
) -> None:
    """Helper to write a hook log file for testing."""
    log_dir = repo_root / ".erk" / "scratch" / "sessions" / session_id / "hooks" / hook_id
    log_dir.mkdir(parents=True, exist_ok=True)

    log_data = {
        "kit_id": "test-kit",
        "hook_id": hook_id,
        "session_id": session_id,
        "started_at": timestamp,
        "ended_at": timestamp,
        "duration_ms": 100,
        "exit_code": exit_code,
        "exit_status": exit_status,
        "stdout": "",
        "stderr": "error output" if exit_status in ("error", "exception") else "",
        "stdin_context": "{}",
        "error_message": error_message,
    }

    log_file = log_dir / f"{timestamp.replace(':', '-')}.json"
    log_file.write_text(json.dumps(log_data), encoding="utf-8")


def test_returns_healthy_when_no_logs(tmp_path: Path) -> None:
    """Test returns healthy status when no logs exist."""
    result = check_hook_health(tmp_path)

    assert result.passed is True
    assert result.name == "hooks"
    assert "no hook logs" in result.message.lower()


def test_returns_healthy_when_all_hooks_succeed(tmp_path: Path) -> None:
    """Test returns healthy when all hooks have success exit status."""
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="test-hook",
        exit_status="success",
        exit_code=0,
        timestamp="2024-01-01T12:00:00+00:00",
    )
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="other-hook",
        exit_status="success",
        exit_code=0,
        timestamp="2024-01-01T12:01:00+00:00",
    )

    result = check_hook_health(tmp_path)

    assert result.passed is True
    assert "healthy" in result.message.lower()
    assert "2 succeeded" in result.message


def test_returns_healthy_when_hooks_blocked(tmp_path: Path) -> None:
    """Test returns healthy when hooks have blocked status (exit code 2)."""
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="test-hook",
        exit_status="blocked",
        exit_code=2,
        timestamp="2024-01-01T12:00:00+00:00",
    )

    result = check_hook_health(tmp_path)

    assert result.passed is True
    assert "1 blocked" in result.message


def test_returns_failure_when_hooks_error(tmp_path: Path) -> None:
    """Test returns failure when hooks have error exit status."""
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="failing-hook",
        exit_status="error",
        exit_code=1,
        timestamp="2024-01-01T12:00:00+00:00",
    )

    result = check_hook_health(tmp_path)

    assert result.passed is False
    assert "1 hook failure" in result.message
    assert result.details is not None
    assert "failing-hook" in result.details


def test_returns_failure_when_hooks_exception(tmp_path: Path) -> None:
    """Test returns failure when hooks have exception exit status."""
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="broken-hook",
        exit_status="exception",
        exit_code=1,
        timestamp="2024-01-01T12:00:00+00:00",
        error_message="ImportError: No module named 'missing'",
    )

    result = check_hook_health(tmp_path)

    assert result.passed is False
    assert "failure" in result.message
    assert result.details is not None
    assert "broken-hook" in result.details


def test_aggregates_multiple_failures(tmp_path: Path) -> None:
    """Test aggregates failures from multiple hooks."""
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="hook-a",
        exit_status="error",
        exit_code=1,
        timestamp="2024-01-01T12:00:00+00:00",
    )
    _write_hook_log(
        tmp_path,
        session_id="session-1",
        hook_id="hook-b",
        exit_status="exception",
        exit_code=1,
        timestamp="2024-01-01T12:01:00+00:00",
    )
    _write_hook_log(
        tmp_path,
        session_id="session-2",
        hook_id="hook-a",
        exit_status="success",
        exit_code=0,
        timestamp="2024-01-01T12:02:00+00:00",
    )

    result = check_hook_health(tmp_path)

    assert result.passed is False
    assert "2 hook failure" in result.message
