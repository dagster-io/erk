"""Unit tests for download-remote-session exec script.

Tests downloading session artifacts from GitHub Actions workflow runs.
Uses FakeGitHub with artifact_download_callback for test isolation.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.download_remote_session import (
    _find_jsonl_file,
    _get_remote_sessions_dir,
)
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session as download_remote_session_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.fake import FakeGitHub

# ============================================================================
# 1. Helper Function Tests (4 tests)
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


def test_find_jsonl_file_success(tmp_path: Path) -> None:
    """Test finding a .jsonl file in a directory."""
    jsonl_file = tmp_path / "session-abc123.jsonl"
    jsonl_file.write_text("{}", encoding="utf-8")

    result = _find_jsonl_file(tmp_path)

    assert result == jsonl_file


def test_find_jsonl_file_not_found(tmp_path: Path) -> None:
    """Test returning None when no .jsonl file exists."""
    # Create a non-jsonl file
    other_file = tmp_path / "other.txt"
    other_file.write_text("hello", encoding="utf-8")

    result = _find_jsonl_file(tmp_path)

    assert result is None


# ============================================================================
# 2. CLI Command Tests (6 tests)
# ============================================================================


def test_cli_missing_run_id() -> None:
    """Test CLI requires --run-id option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--session-id", "test-123"],
    )

    assert result.exit_code != 0
    assert "run-id" in result.output.lower() or "missing" in result.output.lower()


def test_cli_missing_session_id() -> None:
    """Test CLI requires --session-id option."""
    runner = CliRunner()

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", "12345678"],
    )

    assert result.exit_code != 0
    assert "session-id" in result.output.lower() or "missing" in result.output.lower()


def test_cli_success_with_fake_github(tmp_path: Path) -> None:
    """Test successful download using FakeGitHub with callback."""
    session_id = "abc-123"
    run_id = "12345678"

    def download_callback(cb_run_id: str, artifact_name: str, destination: Path) -> bool:
        """Simulate artifact download by creating a session file."""
        session_file = destination / "uploaded-session.jsonl"
        session_file.write_text('{"test": true}\n', encoding="utf-8")
        return True

    fake_github = FakeGitHub(artifact_download_callback=download_callback)
    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, github=fake_github)

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", run_id, "--session-id", session_id],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == session_id
    assert output["run_id"] == run_id
    assert output["artifact_name"] == f"session-{session_id}"
    assert "session.jsonl" in output["path"]

    # Verify the fake tracked the download
    assert len(fake_github.downloaded_artifacts) == 1
    assert fake_github.downloaded_artifacts[0][0] == run_id
    assert fake_github.downloaded_artifacts[0][1] == f"session-{session_id}"


def test_cli_error_artifact_not_found(tmp_path: Path) -> None:
    """Test error when artifact download fails."""
    session_id = "nonexistent-session"
    run_id = "12345678"

    def download_callback(cb_run_id: str, artifact_name: str, destination: Path) -> bool:
        """Simulate download failure."""
        return False

    fake_github = FakeGitHub(artifact_download_callback=download_callback)
    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, github=fake_github)

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", run_id, "--session-id", session_id],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to download" in output["error"]


def test_cli_error_no_jsonl_in_artifact(tmp_path: Path) -> None:
    """Test error when downloaded artifact has no .jsonl file."""
    session_id = "no-jsonl-session"
    run_id = "12345678"

    def download_callback(cb_run_id: str, artifact_name: str, destination: Path) -> bool:
        """Simulate download with no .jsonl file."""
        other_file = destination / "other.txt"
        other_file.write_text("not a session file", encoding="utf-8")
        return True

    fake_github = FakeGitHub(artifact_download_callback=download_callback)
    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, github=fake_github)

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", run_id, "--session-id", session_id],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No .jsonl file found" in output["error"]


def test_cli_cleanup_existing_directory_on_redownload(tmp_path: Path) -> None:
    """Test that existing directory contents are cleaned up on re-download."""
    session_id = "redownload-session"
    run_id = "12345678"

    # Pre-create the session directory with old files
    session_dir = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    session_dir.mkdir(parents=True)
    old_file = session_dir / "old-session.jsonl"
    old_file.write_text('{"old": true}\n', encoding="utf-8")

    def download_callback(cb_run_id: str, artifact_name: str, destination: Path) -> bool:
        """Simulate download with new content."""
        new_file = destination / "new-session.jsonl"
        new_file.write_text('{"new": true}\n', encoding="utf-8")
        return True

    fake_github = FakeGitHub(artifact_download_callback=download_callback)
    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, github=fake_github)

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", run_id, "--session-id", session_id],
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
