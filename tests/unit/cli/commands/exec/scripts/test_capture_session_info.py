"""Unit tests for capture_session_info exec command.

Tests the shell-compatible session info output for CI workflows.
"""

import time
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.capture_session_info import (
    capture_session,
    capture_session_info,
    encode_path_to_project_folder,
)
from erk_shared.context.context import ErkContext
from erk_shared.learn.extraction.claude_installation.fake import FakeClaudeInstallation

# ============================================================================
# 1. capture_session Tests
# ============================================================================


def test_capture_session_success(tmp_path: Path) -> None:
    """Test successful session capture returns session ID and file path."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test" / "repo"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create a session file
    session_file = project_dir / "abc123.jsonl"
    session_file.write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = capture_session(test_cwd, installation)

    assert result is not None
    session_id, session_file_path = result
    assert session_id == "abc123"
    assert session_file_path == str(project_dir / "abc123.jsonl")


def test_capture_session_excludes_agent_logs(tmp_path: Path) -> None:
    """Test that agent logs are excluded from session capture."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create main session (older)
    main_session = project_dir / "main123.jsonl"
    main_session.write_text("{}", encoding="utf-8")

    # Create agent log (newer - should be ignored)
    time.sleep(0.01)
    agent_log = project_dir / "agent-abc123.jsonl"
    agent_log.write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = capture_session(test_cwd, installation)

    assert result is not None
    session_id, _ = result
    assert session_id == "main123"


def test_capture_session_returns_latest(tmp_path: Path) -> None:
    """Test that the most recent non-agent session is returned."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create older session
    older_session = project_dir / "older.jsonl"
    older_session.write_text("{}", encoding="utf-8")

    # Create newer session
    time.sleep(0.01)
    newer_session = project_dir / "newer.jsonl"
    newer_session.write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = capture_session(test_cwd, installation)

    assert result is not None
    session_id, _ = result
    assert session_id == "newer"


def test_capture_session_project_not_found(tmp_path: Path) -> None:
    """Test that None is returned when project directory doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = capture_session(tmp_path / "nonexistent", installation)

    assert result is None


def test_capture_session_no_sessions(tmp_path: Path) -> None:
    """Test that None is returned when no session files exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Only agent logs, no main sessions
    (project_dir / "agent-123.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = capture_session(test_cwd, installation)

    assert result is None


# ============================================================================
# 2. CLI Command Tests
# ============================================================================


def test_cli_success_outputs_shell_variables(tmp_path: Path) -> None:
    """Test CLI outputs shell-compatible variable assignments."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()
    (project_dir / "test123.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    result = runner.invoke(
        capture_session_info,
        ["--path", str(test_cwd)],
        obj=ErkContext.for_test(cwd=tmp_path, claude_installation=installation),
    )

    assert result.exit_code == 0
    assert "SESSION_ID=test123" in result.output
    assert f"SESSION_FILE={project_dir}/test123.jsonl" in result.output


def test_cli_project_not_found_exits_2(tmp_path: Path) -> None:
    """Test CLI exits with code 2 when project directory not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_dir = tmp_path / "test"
    test_dir.mkdir()

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    result = runner.invoke(
        capture_session_info,
        ["--path", str(test_dir)],
        obj=ErkContext.for_test(cwd=tmp_path, claude_installation=installation),
    )

    assert result.exit_code == 2
    assert "Project directory not found for" in result.output


def test_cli_no_sessions_exits_1(tmp_path: Path) -> None:
    """Test CLI exits with code 1 when no sessions exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()
    # Empty project directory - no sessions

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    result = runner.invoke(
        capture_session_info,
        ["--path", str(test_cwd)],
        obj=ErkContext.for_test(cwd=tmp_path, claude_installation=installation),
    )

    assert result.exit_code == 1
    assert "No session file found" in result.output
