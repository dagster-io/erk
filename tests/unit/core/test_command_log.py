"""Unit tests for command_log.py."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from erk.core.command_log import (
    CommandLogEntry,
    _is_logging_disabled,
    _rotate_log_if_needed,
    log_command_end,
    log_command_start,
    read_log_entries,
)


def test_is_logging_disabled_returns_false_when_env_not_set() -> None:
    """Test logging is enabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert _is_logging_disabled() is False


def test_is_logging_disabled_returns_true_when_env_set() -> None:
    """Test logging is disabled when environment variable is set."""
    with patch.dict(os.environ, {"ERK_NO_COMMAND_LOG": "1"}):
        assert _is_logging_disabled() is True


def test_is_logging_disabled_returns_false_when_env_not_one() -> None:
    """Test logging is enabled when environment variable is not '1'."""
    with patch.dict(os.environ, {"ERK_NO_COMMAND_LOG": "0"}):
        assert _is_logging_disabled() is False


def test_log_command_start_returns_none_when_disabled(tmp_path: Path) -> None:
    """Test log_command_start returns None when logging is disabled."""
    with patch.dict(os.environ, {"ERK_NO_COMMAND_LOG": "1"}):
        result = log_command_start(["wt", "delete", "foo"], tmp_path)
        assert result is None


def test_log_command_start_creates_log_file(tmp_path: Path) -> None:
    """Test log_command_start creates the log file."""
    log_path = tmp_path / "command_history.jsonl"

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        with patch("erk.core.command_log._get_current_branch", return_value="main"):
            entry_id = log_command_start(["wt", "delete", "foo"], tmp_path)

    assert entry_id is not None
    assert log_path.exists()


def test_log_command_start_writes_valid_json(tmp_path: Path) -> None:
    """Test log_command_start writes valid JSON to the log file."""
    log_path = tmp_path / "command_history.jsonl"

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        with patch("erk.core.command_log._get_current_branch", return_value="main"):
            log_command_start(["wt", "delete", "foo"], tmp_path)

    content = log_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["command"] == "erk wt delete"
    assert entry["args"] == ["foo"]
    assert entry["cwd"] == str(tmp_path)
    assert entry["branch"] == "main"
    assert entry["exit_code"] is None
    assert "timestamp" in entry
    assert "pid" in entry


def test_log_command_end_writes_completion_entry(tmp_path: Path) -> None:
    """Test log_command_end writes a completion entry."""
    log_path = tmp_path / "command_history.jsonl"

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        with patch("erk.core.command_log._get_current_branch", return_value="main"):
            entry_id = log_command_start(["wt", "delete", "foo"], tmp_path)
            log_command_end(entry_id, 0)

    content = log_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 2

    completion = json.loads(lines[1])
    assert completion["type"] == "completion"
    assert completion["start_timestamp"] == entry_id
    assert completion["exit_code"] == 0


def test_log_command_end_noop_when_entry_id_none() -> None:
    """Test log_command_end does nothing when entry_id is None."""
    # Should not raise any errors
    log_command_end(None, 0)


def test_log_command_start_extracts_subcommand_correctly(tmp_path: Path) -> None:
    """Test command extraction handles nested subcommands."""
    log_path = tmp_path / "command_history.jsonl"

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        with patch("erk.core.command_log._get_current_branch", return_value=None):
            log_command_start(["wt", "delete", "--force", "foo"], tmp_path)

    content = log_path.read_text(encoding="utf-8")
    entry = json.loads(content.strip())
    assert entry["command"] == "erk wt delete"
    assert entry["args"] == ["--force", "foo"]


def test_log_command_start_handles_flags_at_start(tmp_path: Path) -> None:
    """Test command extraction when flags come before subcommand."""
    log_path = tmp_path / "command_history.jsonl"

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        with patch("erk.core.command_log._get_current_branch", return_value=None):
            log_command_start(["--debug", "doctor"], tmp_path)

    content = log_path.read_text(encoding="utf-8")
    entry = json.loads(content.strip())
    # Flags at start mean no subcommand extracted
    assert entry["command"] == "erk"
    assert entry["args"] == ["--debug", "doctor"]


def test_rotate_log_if_needed_does_nothing_when_small(tmp_path: Path) -> None:
    """Test rotation does nothing when file is under size limit."""
    log_path = tmp_path / "command_history.jsonl"
    log_path.write_text("small content\n", encoding="utf-8")

    _rotate_log_if_needed(log_path)

    assert log_path.exists()
    assert not (tmp_path / "command_history.jsonl.old").exists()


def test_rotate_log_if_needed_rotates_large_file(tmp_path: Path) -> None:
    """Test rotation when file exceeds size limit."""
    log_path = tmp_path / "command_history.jsonl"
    # Create a file just over 50MB
    large_content = "x" * (50 * 1024 * 1024 + 100)
    log_path.write_text(large_content, encoding="utf-8")

    _rotate_log_if_needed(log_path)

    assert not log_path.exists()
    old_path = tmp_path / "command_history.jsonl.old"
    assert old_path.exists()


def test_read_log_entries_returns_empty_when_no_file(tmp_path: Path) -> None:
    """Test read_log_entries returns empty list when log file doesn't exist."""
    log_path = tmp_path / "command_history.jsonl"

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=None,
            until=None,
            command_filter=None,
            cwd_filter=None,
            limit=None,
        )

    assert result == []


def test_read_log_entries_parses_entries(tmp_path: Path) -> None:
    """Test read_log_entries correctly parses log entries."""
    log_path = tmp_path / "command_history.jsonl"

    # Write test entries
    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk wt delete",
            "args": ["foo"],
            "cwd": "/test/path",
            "branch": "main",
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
        {
            "timestamp": "2026-01-01T11:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/test/path",
            "branch": "feature",
            "exit_code": None,
            "session_id": None,
            "pid": 12346,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=None,
            until=None,
            command_filter=None,
            cwd_filter=None,
            limit=None,
        )

    assert len(result) == 2
    # Most recent first
    assert result[0].command == "erk doctor"
    assert result[1].command == "erk wt delete"


def test_read_log_entries_filters_by_command(tmp_path: Path) -> None:
    """Test read_log_entries filters by command substring."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk wt delete",
            "args": ["foo"],
            "cwd": "/test/path",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
        {
            "timestamp": "2026-01-01T11:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/test/path",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12346,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=None,
            until=None,
            command_filter="wt delete",
            cwd_filter=None,
            limit=None,
        )

    assert len(result) == 1
    assert result[0].command == "erk wt delete"


def test_read_log_entries_filters_by_cwd(tmp_path: Path) -> None:
    """Test read_log_entries filters by working directory."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/repo/a",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
        {
            "timestamp": "2026-01-01T11:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/repo/b",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12346,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=None,
            until=None,
            command_filter=None,
            cwd_filter="/repo/a",
            limit=None,
        )

    assert len(result) == 1
    assert result[0].cwd == "/repo/a"


def test_read_log_entries_applies_limit(tmp_path: Path) -> None:
    """Test read_log_entries respects limit parameter."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": f"2026-01-01T{10 + i:02d}:00:00+00:00",
            "command": f"erk cmd{i}",
            "args": [],
            "cwd": "/test",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345 + i,
        }
        for i in range(10)
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=None,
            until=None,
            command_filter=None,
            cwd_filter=None,
            limit=3,
        )

    assert len(result) == 3


def test_read_log_entries_joins_completion_data(tmp_path: Path) -> None:
    """Test read_log_entries joins exit code from completion entries."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/test",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
        {
            "timestamp": "2026-01-01T10:00:01+00:00",
            "type": "completion",
            "start_timestamp": "2026-01-01T10:00:00+00:00",
            "exit_code": 0,
            "pid": 12345,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=None,
            until=None,
            command_filter=None,
            cwd_filter=None,
            limit=None,
        )

    assert len(result) == 1
    assert result[0].exit_code == 0


def test_read_log_entries_filters_by_since(tmp_path: Path) -> None:
    """Test read_log_entries filters by since datetime."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T08:00:00+00:00",
            "command": "erk old",
            "args": [],
            "cwd": "/test",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
        {
            "timestamp": "2026-01-01T12:00:00+00:00",
            "command": "erk new",
            "args": [],
            "cwd": "/test",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12346,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    since = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = read_log_entries(
            since=since,
            until=None,
            command_filter=None,
            cwd_filter=None,
            limit=None,
        )

    assert len(result) == 1
    assert result[0].command == "erk new"


def test_command_log_entry_is_frozen() -> None:
    """Test CommandLogEntry is a frozen dataclass."""
    entry = CommandLogEntry(
        timestamp="2026-01-01T10:00:00+00:00",
        command="erk doctor",
        args=(),
        cwd="/test",
        branch="main",
        exit_code=0,
        session_id=None,
        pid=12345,
    )

    # Verify it's frozen by checking hash works
    hash(entry)

    # Verify attributes are set correctly
    assert entry.command == "erk doctor"
    assert entry.exit_code == 0
