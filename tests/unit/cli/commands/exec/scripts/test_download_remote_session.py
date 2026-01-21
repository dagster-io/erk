"""Unit tests for download-remote-session exec script.

Tests downloading session files from GitHub Gist URLs.
Uses monkeypatching to simulate URL fetch responses.
"""

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.download_remote_session import (
    _get_remote_sessions_dir,
)
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session as download_remote_session_command,
)
from erk_shared.context.context import ErkContext

# ============================================================================
# 1. Helper Function Tests (2 tests)
# ============================================================================


def test_get_remote_sessions_dir_creates_directory(tmp_path: Path) -> None:
    """Test that the remote sessions directory is created if it doesn't exist."""
    session_id = "test-session-123"

    result = _get_remote_sessions_dir(tmp_path, session_id)

    expected = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    assert result == expected
    assert result.exists()
    assert result.is_dir()


def test_get_remote_sessions_dir_returns_existing(tmp_path: Path) -> None:
    """Test that existing directory is returned without error."""
    session_id = "existing-session"
    expected = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    expected.mkdir(parents=True)

    result = _get_remote_sessions_dir(tmp_path, session_id)

    assert result == expected


# ============================================================================
# 2. CLI Command Tests (5 tests)
# ============================================================================


def test_cli_missing_gist_url() -> None:
    """Test CLI requires --gist-url option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--session-id", "test-123"],
    )

    assert result.exit_code != 0
    assert "gist-url" in result.output.lower() or "missing" in result.output.lower()


def test_cli_missing_session_id() -> None:
    """Test CLI requires --session-id option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--gist-url", "https://gist.githubusercontent.com/user/abc/raw/session.jsonl"],
    )

    assert result.exit_code != 0
    assert "session-id" in result.output.lower() or "missing" in result.output.lower()


def test_cli_success_with_gist_download(tmp_path: Path) -> None:
    """Test successful download from gist URL."""
    session_id = "abc-123"
    gist_url = "https://gist.githubusercontent.com/user/abc123/raw/session.jsonl"
    session_content = '{"type": "assistant"}\n{"type": "user"}\n'

    # Mock urllib.request.urlopen to return session content
    mock_response = MagicMock()
    mock_response.read.return_value = session_content.encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = runner.invoke(
            download_remote_session_command,
            ["--gist-url", gist_url, "--session-id", session_id],
            obj=ctx,
        )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == session_id
    assert output["source"] == "gist"
    assert "session.jsonl" in output["path"]

    # Verify the file was created with correct content
    session_file = Path(output["path"])
    assert session_file.exists()
    assert session_file.read_text(encoding="utf-8") == session_content


def test_cli_error_gist_download_fails(tmp_path: Path) -> None:
    """Test error when gist URL cannot be fetched."""
    session_id = "bad-session"
    gist_url = "https://gist.githubusercontent.com/user/nonexistent/raw/session.jsonl"

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("404 Not Found"),
    ):
        result = runner.invoke(
            download_remote_session_command,
            ["--gist-url", gist_url, "--session-id", session_id],
            obj=ctx,
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to download from gist URL" in output["error"]


def test_cli_cleanup_existing_directory_on_redownload(tmp_path: Path) -> None:
    """Test that existing directory contents are cleaned up on re-download."""
    session_id = "redownload-session"
    gist_url = "https://gist.githubusercontent.com/user/abc/raw/session.jsonl"
    new_content = '{"new": true}\n'

    # Pre-create the session directory with old files
    session_dir = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    session_dir.mkdir(parents=True)
    old_file = session_dir / "old-session.jsonl"
    old_file.write_text('{"old": true}\n', encoding="utf-8")

    # Mock urllib.request.urlopen to return new content
    mock_response = MagicMock()
    mock_response.read.return_value = new_content.encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = runner.invoke(
            download_remote_session_command,
            ["--gist-url", gist_url, "--session-id", session_id],
            obj=ctx,
        )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify old file was cleaned up and new file exists as session.jsonl
    assert not old_file.exists()
    session_file = session_dir / "session.jsonl"
    assert session_file.exists()
    content = session_file.read_text(encoding="utf-8")
    assert "new" in content
