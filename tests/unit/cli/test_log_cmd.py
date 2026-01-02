"""Tests for the erk log command."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import click
from click.testing import CliRunner

from erk.cli.commands.log_cmd import _parse_since, log_cmd


def test_parse_since_returns_none_for_none() -> None:
    """Test _parse_since returns None for None input."""
    assert _parse_since(None) is None


def test_parse_since_parses_hours_ago() -> None:
    """Test _parse_since parses 'N hours ago'."""
    with patch("erk.cli.commands.log_cmd.datetime") as mock_dt:
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        result = _parse_since("2 hours ago")

    expected = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert result == expected


def test_parse_since_parses_days_ago() -> None:
    """Test _parse_since parses 'N days ago'."""
    with patch("erk.cli.commands.log_cmd.datetime") as mock_dt:
        now = datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        result = _parse_since("3 days ago")

    expected = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
    assert result == expected


def test_parse_since_parses_iso_format() -> None:
    """Test _parse_since parses ISO format datetime."""
    result = _parse_since("2026-01-01T10:00:00+00:00")

    expected = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert result == expected


def test_parse_since_raises_for_invalid_format() -> None:
    """Test _parse_since raises BadParameter for invalid format."""
    try:
        _parse_since("invalid time")
        raise AssertionError("Should have raised BadParameter")
    except click.BadParameter as e:
        assert "Invalid time format" in str(e)


def test_log_cmd_shows_no_entries_message(tmp_path: Path) -> None:
    """Test log command shows message when no entries found."""
    log_path = tmp_path / "command_history.jsonl"

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd)

    assert result.exit_code == 0
    assert "No matching entries found" in result.output


def test_log_cmd_displays_entries(tmp_path: Path) -> None:
    """Test log command displays log entries."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/test/path",
            "branch": "main",
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd, ["--full"])

    assert result.exit_code == 0
    assert "erk doctor" in result.output


def test_log_cmd_shows_exit_status_indicators(tmp_path: Path) -> None:
    """Test log command shows correct status indicators."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk success",
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
        {
            "timestamp": "2026-01-01T11:00:00+00:00",
            "command": "erk failure",
            "args": [],
            "cwd": "/test",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12346,
        },
        {
            "timestamp": "2026-01-01T11:00:01+00:00",
            "type": "completion",
            "start_timestamp": "2026-01-01T11:00:00+00:00",
            "exit_code": 1,
            "pid": 12346,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd, ["--full"])

    assert result.exit_code == 0
    # Check for success/failure indicators (green checkmark, red X)
    assert "✓" in result.output or "✗" in result.output


def test_log_cmd_respects_filter_option(tmp_path: Path) -> None:
    """Test log command --filter option."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk wt delete",
            "args": ["foo"],
            "cwd": "/test",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
        {
            "timestamp": "2026-01-01T11:00:00+00:00",
            "command": "erk doctor",
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

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd, ["--filter", "wt delete"])

    assert result.exit_code == 0
    assert "wt delete" in result.output
    assert "doctor" not in result.output


def test_log_cmd_respects_limit_option(tmp_path: Path) -> None:
    """Test log command --limit option."""
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

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd, ["-n", "3"])

    assert result.exit_code == 0
    # Should show limit message
    assert "Showing 3 most recent" in result.output


def test_log_cmd_shows_cwd_when_requested(tmp_path: Path) -> None:
    """Test log command --show-cwd option."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/special/path",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd, ["--show-cwd"])

    assert result.exit_code == 0
    assert "/special/path" in result.output


def test_log_cmd_hides_cwd_by_default(tmp_path: Path) -> None:
    """Test log command hides cwd by default."""
    log_path = tmp_path / "command_history.jsonl"

    entries = [
        {
            "timestamp": "2026-01-01T10:00:00+00:00",
            "command": "erk doctor",
            "args": [],
            "cwd": "/unique/hidden/path",
            "branch": None,
            "exit_code": None,
            "session_id": None,
            "pid": 12345,
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    log_path.write_text(content, encoding="utf-8")

    runner = CliRunner()
    with patch("erk.core.command_log._get_log_file_path", return_value=log_path):
        result = runner.invoke(log_cmd)

    assert result.exit_code == 0
    assert "/unique/hidden/path" not in result.output
