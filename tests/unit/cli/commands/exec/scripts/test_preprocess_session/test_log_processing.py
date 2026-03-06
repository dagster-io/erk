"""Log file processing tests for session log preprocessing."""

import json
from pathlib import Path

import pytest

from erk.cli.commands.exec.scripts.preprocess_session import process_log_file
from tests.unit.cli.commands.exec.scripts import fixtures


def test_process_log_file_filters_file_history_snapshot(tmp_path: Path) -> None:
    """Test that file-history-snapshot entries are filtered out."""
    log_file = tmp_path / "test.jsonl"
    # Parse and re-serialize to ensure valid JSON
    snapshot_json = json.dumps(json.loads(fixtures.JSONL_FILE_HISTORY_SNAPSHOT))
    user_json = json.dumps(json.loads(fixtures.JSONL_USER_MESSAGE_STRING))
    log_file.write_text(
        f"{snapshot_json}\n{user_json}",
        encoding="utf-8",
    )

    entries, _total, _skipped = process_log_file(log_file)
    assert len(entries) == 1  # Only user message, snapshot filtered
    assert entries[0]["type"] == "user"


def test_process_log_file_strips_metadata(tmp_path: Path) -> None:
    """Test that metadata fields are stripped."""
    log_file = tmp_path / "test.jsonl"
    user_json = json.dumps(json.loads(fixtures.JSONL_USER_MESSAGE_STRING))
    log_file.write_text(user_json, encoding="utf-8")

    entries, _total, _skipped = process_log_file(log_file)
    # Should NOT have metadata fields
    assert "parentUuid" not in entries[0]
    assert "sessionId" not in entries[0]
    assert "cwd" not in entries[0]
    assert "timestamp" not in entries[0]
    assert "userType" not in entries[0]
    assert "isSidechain" not in entries[0]


def test_process_log_file_preserves_usage_field(tmp_path: Path) -> None:
    """Test that usage metadata is preserved in assistant messages."""
    log_file = tmp_path / "test.jsonl"
    log_file.write_text(json.dumps(json.loads(fixtures.JSONL_ASSISTANT_TEXT)), encoding="utf-8")

    entries, _total, _skipped = process_log_file(log_file)
    assert "usage" in entries[0]["message"]
    assert entries[0]["message"]["usage"]["input_tokens"] == 100
    assert entries[0]["message"]["usage"]["output_tokens"] == 50


def test_process_log_file_preserves_git_branch(tmp_path: Path) -> None:
    """Test that gitBranch is preserved for metadata extraction."""
    log_file = tmp_path / "test.jsonl"
    user_json = json.dumps(json.loads(fixtures.JSONL_USER_MESSAGE_STRING))
    log_file.write_text(user_json, encoding="utf-8")

    entries, _total, _skipped = process_log_file(log_file)
    assert entries[0]["gitBranch"] == "test-branch"


def test_process_log_file_handles_empty_file(tmp_path: Path) -> None:
    """Test handling of empty log file."""
    log_file = tmp_path / "empty.jsonl"
    log_file.write_text("", encoding="utf-8")

    entries, _total, _skipped = process_log_file(log_file)
    assert entries == []


def test_process_log_file_handles_malformed_json(tmp_path: Path) -> None:
    """Test handling of malformed JSON lines."""
    log_file = tmp_path / "malformed.jsonl"
    log_file.write_text("{invalid json}", encoding="utf-8")

    # Should raise JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        process_log_file(log_file)
