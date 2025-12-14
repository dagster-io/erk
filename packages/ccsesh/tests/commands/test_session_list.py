"""Tests for ccsesh session list command."""

import time
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from ccsesh.commands.session import (
    encode_path_to_project_id,
    resolve_project_dir,
    session,
)


def test_encode_path_to_project_id() -> None:
    """Test path encoding matches Claude Code format."""
    path = Path("/Users/alice/code/myapp")
    result = encode_path_to_project_id(path)
    assert result == "-Users-alice-code-myapp"


def test_resolve_project_dir_with_project_id(tmp_path: Path) -> None:
    """Test resolving project directory using --project-id."""
    # Arrange: Create a project directory
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-Users-alice-code-myapp"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = resolve_project_dir(project_id, None, tmp_path)

        # Assert
        assert result == project_dir


def test_resolve_project_dir_with_project_path(tmp_path: Path) -> None:
    """Test resolving project directory using --project-path."""
    # Arrange: Create a project directory with encoded path
    projects_dir = tmp_path / ".claude" / "projects"
    project_path = tmp_path / "myproject"
    project_path.mkdir(parents=True)
    encoded = str(project_path.resolve()).replace("/", "-")
    project_dir = projects_dir / encoded
    project_dir.mkdir(parents=True)

    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = resolve_project_dir(None, str(project_path), tmp_path)

        # Assert
        assert result == project_dir


def test_resolve_project_dir_from_cwd(tmp_path: Path) -> None:
    """Test resolving project directory from current working directory."""
    # Arrange: Create a project directory from cwd
    projects_dir = tmp_path / ".claude" / "projects"
    cwd = tmp_path / "workspace"
    cwd.mkdir(parents=True)
    encoded = str(cwd.resolve()).replace("/", "-")
    project_dir = projects_dir / encoded
    project_dir.mkdir(parents=True)

    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = resolve_project_dir(None, None, cwd)

        # Assert
        assert result == project_dir


def test_resolve_project_dir_returns_none_when_not_found(tmp_path: Path) -> None:
    """Test that resolve_project_dir returns None when project doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        result = resolve_project_dir("nonexistent-project", None, tmp_path)
        assert result is None


def test_session_list_shows_sessions_sorted_by_mtime(tmp_path: Path) -> None:
    """Test that session list shows sessions sorted by modification time."""
    # Arrange: Create project with multiple sessions
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    # Create session files with different mtimes
    session1 = project_dir / "session-old.jsonl"
    session2 = project_dir / "session-new.jsonl"

    session1.write_text("{}", encoding="utf-8")
    time.sleep(0.01)  # Small delay to ensure different mtimes
    session2.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(session, ["list", "--project-id", project_id])

        # Assert
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        # Newest first
        assert lines[0] == "session-new"
        assert lines[1] == "session-old"


def test_session_list_excludes_agent_files(tmp_path: Path) -> None:
    """Test that agent-*.jsonl files are excluded from session list."""
    # Arrange: Create project with session and agent files
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-abc123.jsonl"
    agent_file = project_dir / "agent-xyz789.jsonl"

    session_file.write_text("{}", encoding="utf-8")
    agent_file.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(session, ["list", "--project-id", project_id])

        # Assert
        assert result.exit_code == 0
        assert "session-abc123" in result.output
        assert "agent-xyz789" not in result.output


def test_session_list_shows_no_sessions_message(tmp_path: Path) -> None:
    """Test that appropriate message is shown when no sessions exist."""
    # Arrange: Create empty project directory
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    runner = CliRunner()
    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(session, ["list", "--project-id", project_id])

        # Assert
        assert result.exit_code == 0
        assert "No sessions found." in result.output


def test_session_list_error_when_project_not_found(tmp_path: Path) -> None:
    """Test error message when project directory doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    runner = CliRunner()
    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(session, ["list", "--project-id", "nonexistent"])

        # Assert
        assert result.exit_code == 1
        assert "Project not found: nonexistent" in result.output


def test_session_list_only_includes_jsonl_files(tmp_path: Path) -> None:
    """Test that only .jsonl files are included in session list."""
    # Arrange: Create project with various file types
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-valid.jsonl"
    txt_file = project_dir / "notes.txt"
    json_file = project_dir / "config.json"

    session_file.write_text("{}", encoding="utf-8")
    txt_file.write_text("notes", encoding="utf-8")
    json_file.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(session, ["list", "--project-id", project_id])

        # Assert
        assert result.exit_code == 0
        assert "session-valid" in result.output
        assert "notes" not in result.output
        assert "config" not in result.output


def test_session_list_ignores_directories(tmp_path: Path) -> None:
    """Test that directories are ignored in session list."""
    # Arrange: Create project with a subdirectory
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-valid.jsonl"
    subdir = project_dir / "subdir.jsonl"  # Directory named like a session

    session_file.write_text("{}", encoding="utf-8")
    subdir.mkdir()

    runner = CliRunner()
    with patch("ccsesh.commands.session.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(session, ["list", "--project-id", project_id])

        # Assert
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().split("\n") if line]
        assert len(lines) == 1
        assert lines[0] == "session-valid"
