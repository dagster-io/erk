"""Unit tests for download-remote-session exec script.

Tests downloading session artifacts from GitHub Actions workflow runs.
Uses monkeypatch for subprocess mocking and tmp_path for filesystem isolation.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.download_remote_session import (
    _find_jsonl_file,
    _get_remote_sessions_dir,
)
from erk.cli.commands.exec.scripts.download_remote_session import (
    download_remote_session as download_remote_session_command,
)
from erk_shared.context.context import ErkContext

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


def test_cli_success_with_mocked_subprocess(
    tmp_path: Path,
    monkeypatch: MagicMock,
) -> None:
    """Test successful download with mocked subprocess."""
    session_id = "abc-123"
    run_id = "12345678"

    # Mock subprocess to simulate successful gh run download
    def mock_run(
        cmd: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        # When gh run download is called, create a .jsonl file in the target dir
        if "gh" in cmd and "run" in cmd and "download" in cmd:
            # Find the --dir argument
            dir_index = cmd.index("--dir") + 1
            target_dir = Path(cmd[dir_index])
            target_dir.mkdir(parents=True, exist_ok=True)
            # Create the session file
            session_file = target_dir / "uploaded-session.jsonl"
            session_file.write_text('{"test": true}\n', encoding="utf-8")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

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


def test_cli_error_artifact_not_found(
    tmp_path: Path,
    monkeypatch: MagicMock,
) -> None:
    """Test error when artifact download fails."""
    session_id = "nonexistent-session"
    run_id = "12345678"

    # Mock subprocess to simulate failed gh run download
    # We need to raise CalledProcessError when check=True is passed
    def mock_run(
        cmd: list[str],
        *,
        check: bool = False,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if check:
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=cmd,
                output="",  # CalledProcessError uses 'output' not 'stdout'
                stderr="no artifact found",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="no artifact found",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", run_id, "--session-id", session_id],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to download" in output["error"]


def test_cli_error_no_jsonl_in_artifact(
    tmp_path: Path,
    monkeypatch: MagicMock,
) -> None:
    """Test error when downloaded artifact has no .jsonl file."""
    session_id = "no-jsonl-session"
    run_id = "12345678"

    # Mock subprocess to simulate successful download but no .jsonl file
    def mock_run(
        cmd: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if "gh" in cmd and "run" in cmd and "download" in cmd:
            # Find the --dir argument and create directory but no .jsonl file
            dir_index = cmd.index("--dir") + 1
            target_dir = Path(cmd[dir_index])
            target_dir.mkdir(parents=True, exist_ok=True)
            # Create a non-jsonl file
            other_file = target_dir / "other.txt"
            other_file.write_text("not a session file", encoding="utf-8")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

    result = runner.invoke(
        download_remote_session_command,
        ["--run-id", run_id, "--session-id", session_id],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No .jsonl file found" in output["error"]


def test_cli_cleanup_existing_directory_on_redownload(
    tmp_path: Path,
    monkeypatch: MagicMock,
) -> None:
    """Test that existing directory contents are cleaned up on re-download."""
    session_id = "redownload-session"
    run_id = "12345678"

    # Pre-create the session directory with old files
    session_dir = tmp_path / ".erk" / "scratch" / "remote-sessions" / session_id
    session_dir.mkdir(parents=True)
    old_file = session_dir / "old-session.jsonl"
    old_file.write_text('{"old": true}\n', encoding="utf-8")

    # Mock subprocess to simulate successful download with new content
    def mock_run(
        cmd: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if "gh" in cmd and "run" in cmd and "download" in cmd:
            dir_index = cmd.index("--dir") + 1
            target_dir = Path(cmd[dir_index])
            target_dir.mkdir(parents=True, exist_ok=True)
            # Create new session file
            new_file = target_dir / "new-session.jsonl"
            new_file.write_text('{"new": true}\n', encoding="utf-8")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path)

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
