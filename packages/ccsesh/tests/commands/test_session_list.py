"""Tests for ccsesh session list command."""

import time
from pathlib import Path

from click.testing import CliRunner

from ccsesh.api.projects import encode_path_to_project_id
from ccsesh.api.sessions import get_project_dir_by_id, get_project_dir_by_path, list_sessions
from ccsesh.cli import CcseshContext
from ccsesh.commands.session import session


def test_encode_path_to_project_id() -> None:
    """Test path encoding matches Claude Code format."""
    path = Path("/Users/alice/code/myapp")
    result = encode_path_to_project_id(path)
    assert result == "-Users-alice-code-myapp"


def test_get_project_dir_by_id(tmp_path: Path) -> None:
    """Test resolving project directory by project ID."""
    # Arrange: Create a project directory
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-Users-alice-code-myapp"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    # Act
    result = get_project_dir_by_id(project_id, projects_dir=projects_dir)

    # Assert
    assert result == project_dir


def test_get_project_dir_by_id_returns_none_when_not_found(tmp_path: Path) -> None:
    """Test that get_project_dir_by_id returns None when project doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    result = get_project_dir_by_id("nonexistent-project", projects_dir=projects_dir)
    assert result is None


def test_get_project_dir_by_path(tmp_path: Path) -> None:
    """Test resolving project directory by filesystem path."""
    # Arrange: Create a project directory with encoded path
    projects_dir = tmp_path / ".claude" / "projects"
    project_path = tmp_path / "myproject"
    project_path.mkdir(parents=True)
    encoded = str(project_path.resolve()).replace("/", "-")
    project_dir = projects_dir / encoded
    project_dir.mkdir(parents=True)

    # Act
    result = get_project_dir_by_path(project_path, projects_dir=projects_dir)

    # Assert
    assert result == project_dir


def test_get_project_dir_by_path_returns_none_when_not_found(tmp_path: Path) -> None:
    """Test that get_project_dir_by_path returns None when project doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)
    project_path = tmp_path / "nonexistent"

    result = get_project_dir_by_path(project_path, projects_dir=projects_dir)
    assert result is None


def test_list_sessions_returns_session_ids_sorted_by_mtime(tmp_path: Path) -> None:
    """Test that list_sessions returns session IDs sorted by mtime."""
    # Arrange: Create project with multiple sessions
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)

    session1 = project_dir / "session-old.jsonl"
    session2 = project_dir / "session-new.jsonl"

    session1.write_text("{}", encoding="utf-8")
    time.sleep(0.01)  # Small delay to ensure different mtimes
    session2.write_text("{}", encoding="utf-8")

    # Act
    result = list_sessions(project_dir)

    # Assert
    assert len(result) == 2
    assert result[0] == "session-new"  # Newest first
    assert result[1] == "session-old"


def test_list_sessions_excludes_agent_files(tmp_path: Path) -> None:
    """Test that agent-*.jsonl files are excluded from list_sessions."""
    # Arrange: Create project with session and agent files
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-abc123.jsonl"
    agent_file = project_dir / "agent-xyz789.jsonl"

    session_file.write_text("{}", encoding="utf-8")
    agent_file.write_text("{}", encoding="utf-8")

    # Act
    result = list_sessions(project_dir)

    # Assert
    assert "session-abc123" in result
    assert "agent-xyz789" not in result


def test_list_sessions_only_includes_jsonl_files(tmp_path: Path) -> None:
    """Test that only .jsonl files are included in list_sessions."""
    # Arrange: Create project with various file types
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-valid.jsonl"
    txt_file = project_dir / "notes.txt"
    json_file = project_dir / "config.json"

    session_file.write_text("{}", encoding="utf-8")
    txt_file.write_text("notes", encoding="utf-8")
    json_file.write_text("{}", encoding="utf-8")

    # Act
    result = list_sessions(project_dir)

    # Assert
    assert result == ["session-valid"]


def test_list_sessions_ignores_directories(tmp_path: Path) -> None:
    """Test that directories are ignored in list_sessions."""
    # Arrange: Create project with a subdirectory
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-valid.jsonl"
    subdir = project_dir / "subdir.jsonl"  # Directory named like a session

    session_file.write_text("{}", encoding="utf-8")
    subdir.mkdir()

    # Act
    result = list_sessions(project_dir)

    # Assert
    assert result == ["session-valid"]


# CLI integration tests (thin wrapper tests)


def test_session_list_cli_shows_sessions(tmp_path: Path) -> None:
    """Test that session list CLI shows sessions from API."""
    # Arrange: Create project with sessions
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    session1 = project_dir / "session-old.jsonl"
    session2 = project_dir / "session-new.jsonl"

    session1.write_text("{}", encoding="utf-8")
    time.sleep(0.01)
    session2.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    from unittest.mock import patch

    with patch("ccsesh.api.sessions.get_projects_dir", return_value=projects_dir):
        # Act: Invoke with context object set
        result = runner.invoke(
            session, ["list", "--project-id", project_id], obj=CcseshContext(cwd=tmp_path)
        )

        # Assert
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "session-new"
        assert lines[1] == "session-old"


def test_session_list_cli_shows_no_sessions_message(tmp_path: Path) -> None:
    """Test that appropriate message is shown when no sessions exist."""
    # Arrange: Create empty project directory
    projects_dir = tmp_path / ".claude" / "projects"
    project_id = "-test-project"
    project_dir = projects_dir / project_id
    project_dir.mkdir(parents=True)

    runner = CliRunner()
    from unittest.mock import patch

    with patch("ccsesh.api.sessions.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(
            session, ["list", "--project-id", project_id], obj=CcseshContext(cwd=tmp_path)
        )

        # Assert
        assert result.exit_code == 0
        assert "No sessions found." in result.output


def test_session_list_cli_error_when_project_not_found(tmp_path: Path) -> None:
    """Test error message when project directory doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    runner = CliRunner()
    from unittest.mock import patch

    with patch("ccsesh.api.sessions.get_projects_dir", return_value=projects_dir):
        # Act
        result = runner.invoke(
            session, ["list", "--project-id", "nonexistent"], obj=CcseshContext(cwd=tmp_path)
        )

        # Assert
        assert result.exit_code == 1
        assert "Project not found: nonexistent" in result.output


def test_session_list_cli_mutual_exclusivity(tmp_path: Path) -> None:
    """Test that --project-id and --project-path are mutually exclusive."""
    runner = CliRunner()

    # Act
    result = runner.invoke(
        session,
        ["list", "--project-id", "some-id", "--project-path", "/some/path"],
        obj=CcseshContext(cwd=tmp_path),
    )

    # Assert
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_session_list_cli_uses_cwd_from_context(tmp_path: Path) -> None:
    """Test that CLI uses cwd from context when no options provided."""
    # Arrange: Create project matching cwd
    projects_dir = tmp_path / ".claude" / "projects"
    cwd = tmp_path / "myproject"
    cwd.mkdir(parents=True)
    encoded = str(cwd.resolve()).replace("/", "-")
    project_dir = projects_dir / encoded
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-abc.jsonl"
    session_file.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    from unittest.mock import patch

    with patch("ccsesh.api.sessions.get_projects_dir", return_value=projects_dir):
        # Act: Invoke with cwd set to myproject
        result = runner.invoke(session, ["list"], obj=CcseshContext(cwd=cwd))

        # Assert
        assert result.exit_code == 0
        assert "session-abc" in result.output


def test_session_list_cli_relative_project_path(tmp_path: Path) -> None:
    """Test that --project-path supports relative paths resolved against ctx.cwd."""
    # Arrange: Create project for a subdirectory
    projects_dir = tmp_path / ".claude" / "projects"
    cwd = tmp_path / "workspace"
    cwd.mkdir(parents=True)
    subdir = cwd / "myproject"
    subdir.mkdir(parents=True)
    encoded = str(subdir.resolve()).replace("/", "-")
    project_dir = projects_dir / encoded
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-xyz.jsonl"
    session_file.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    from unittest.mock import patch

    with patch("ccsesh.api.sessions.get_projects_dir", return_value=projects_dir):
        # Act: Use relative path from cwd
        result = runner.invoke(
            session, ["list", "--project-path", "myproject"], obj=CcseshContext(cwd=cwd)
        )

        # Assert
        assert result.exit_code == 0
        assert "session-xyz" in result.output
