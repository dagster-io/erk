"""Tests for session discovery module."""

from pathlib import Path

from erk_shared.extraction.fake_session_environment import FakeSessionEnvironment, FileEntry
from erk_shared.extraction.session_discovery import (
    discover_sessions,
    encode_path_to_project_folder,
    find_project_dir,
    get_branch_context,
    get_current_session_id,
)
from erk_shared.git.fake import FakeGit


class TestGetCurrentSessionId:
    """Tests for get_current_session_id function."""

    def test_extracts_session_id_from_env(self) -> None:
        """Session ID is extracted from SESSION_CONTEXT env var."""
        env = FakeSessionEnvironment(session_context="session_id=abc123-def456")
        result = get_current_session_id(env)
        assert result == "abc123-def456"

    def test_returns_none_when_not_set(self) -> None:
        """Returns None when SESSION_CONTEXT is not set."""
        env = FakeSessionEnvironment(session_context=None)
        result = get_current_session_id(env)
        assert result is None

    def test_returns_none_when_invalid_format(self) -> None:
        """Returns None when SESSION_CONTEXT has invalid format."""
        env = FakeSessionEnvironment(session_context="invalid_format")
        result = get_current_session_id(env)
        assert result is None


class TestGetBranchContext:
    """Tests for get_branch_context function."""

    def test_returns_branch_context(self, tmp_path: Path) -> None:
        """Returns BranchContext with current and trunk branch info."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )

        result = get_branch_context(git, tmp_path)

        assert result.current_branch == "feature-x"
        assert result.trunk_branch == "main"
        assert result.is_on_trunk is False

    def test_detects_on_trunk(self, tmp_path: Path) -> None:
        """Correctly detects when on trunk branch."""
        git = FakeGit(
            current_branches={tmp_path: "main"},
            default_branches={tmp_path: "main"},
        )

        result = get_branch_context(git, tmp_path)

        assert result.current_branch == "main"
        assert result.trunk_branch == "main"
        assert result.is_on_trunk is True


class TestDiscoverSessions:
    """Tests for discover_sessions function."""

    def test_discovers_sessions_in_project_dir(self) -> None:
        """Discovers session JSONL files in project directory."""
        project_dir = Path("/fake/project")
        session1 = project_dir / "session1.jsonl"
        session2 = project_dir / "session2.jsonl"

        env = FakeSessionEnvironment(
            files={
                session1: FileEntry(content="{}", mtime=1000.0),
                session2: FileEntry(content="{}", mtime=2000.0),
            }
        )

        result = discover_sessions(
            project_dir=project_dir,
            current_session_id=None,
            env=env,
            min_size=0,
            limit=10,
        )

        assert len(result) == 2
        session_ids = {s.session_id for s in result}
        assert session_ids == {"session1", "session2"}

    def test_excludes_agent_logs(self) -> None:
        """Agent log files are excluded from results."""
        project_dir = Path("/fake/project")
        session1 = project_dir / "session1.jsonl"
        agent_log = project_dir / "agent-abc123.jsonl"

        env = FakeSessionEnvironment(
            files={
                session1: FileEntry(content="{}", mtime=1000.0),
                agent_log: FileEntry(content="{}", mtime=2000.0),
            }
        )

        result = discover_sessions(
            project_dir=project_dir,
            current_session_id=None,
            env=env,
            min_size=0,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].session_id == "session1"

    def test_excludes_non_jsonl_files(self) -> None:
        """Non-JSONL files are excluded from results."""
        project_dir = Path("/fake/project")
        session1 = project_dir / "session1.jsonl"
        config = project_dir / "config.json"
        notes = project_dir / "notes.txt"

        env = FakeSessionEnvironment(
            files={
                session1: FileEntry(content="{}", mtime=1000.0),
                config: FileEntry(content="{}", mtime=2000.0),
                notes: FileEntry(content="notes", mtime=3000.0),
            }
        )

        result = discover_sessions(
            project_dir=project_dir,
            current_session_id=None,
            env=env,
            min_size=0,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].session_id == "session1"

    def test_filters_by_min_size(self) -> None:
        """Sessions below min_size are filtered out."""
        project_dir = Path("/fake/project")
        small = project_dir / "small.jsonl"
        large = project_dir / "large.jsonl"

        env = FakeSessionEnvironment(
            files={
                small: FileEntry(content="{}", mtime=1000.0),  # ~2 bytes
                large: FileEntry(content="x" * 1000, mtime=2000.0),  # 1000 bytes
            }
        )

        result = discover_sessions(
            project_dir=project_dir,
            current_session_id=None,
            env=env,
            min_size=500,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].session_id == "large"

    def test_respects_limit(self) -> None:
        """Only returns up to limit sessions."""
        project_dir = Path("/fake/project")

        files = {
            project_dir / f"session{i}.jsonl": FileEntry(content="{}", mtime=float(i))
            for i in range(5)
        }
        env = FakeSessionEnvironment(files=files)

        result = discover_sessions(
            project_dir=project_dir,
            current_session_id=None,
            env=env,
            min_size=0,
            limit=3,
        )

        assert len(result) == 3

    def test_marks_current_session(self) -> None:
        """Current session is marked with is_current=True."""
        project_dir = Path("/fake/project")
        session1 = project_dir / "session1.jsonl"
        session2 = project_dir / "session2.jsonl"

        env = FakeSessionEnvironment(
            files={
                session1: FileEntry(content="{}", mtime=1000.0),
                session2: FileEntry(content="{}", mtime=2000.0),
            }
        )

        result = discover_sessions(
            project_dir=project_dir,
            current_session_id="session1",
            env=env,
            min_size=0,
            limit=10,
        )

        session1_result = next(s for s in result if s.session_id == "session1")
        session2_result = next(s for s in result if s.session_id == "session2")

        assert session1_result.is_current is True
        assert session2_result.is_current is False

    def test_returns_empty_for_nonexistent_dir(self) -> None:
        """Returns empty list for non-existent project directory."""
        env = FakeSessionEnvironment()  # No directories

        result = discover_sessions(
            project_dir=Path("/nonexistent"),
            current_session_id=None,
            env=env,
            min_size=0,
            limit=10,
        )

        assert len(result) == 0


class TestEncodePathToProjectFolder:
    """Tests for encode_path_to_project_folder function."""

    def test_replaces_slashes_with_dashes(self) -> None:
        """Forward slashes are replaced with dashes."""
        result = encode_path_to_project_folder(Path("/Users/foo/bar"))
        assert result == "-Users-foo-bar"

    def test_replaces_dots_with_dashes(self) -> None:
        """Dots are replaced with dashes."""
        result = encode_path_to_project_folder(Path("/Users/foo/.config"))
        assert result == "-Users-foo--config"


class TestFindProjectDir:
    """Tests for find_project_dir function."""

    def test_returns_none_if_projects_dir_not_exists(self) -> None:
        """Returns None if ~/.claude/projects/ doesn't exist."""
        env = FakeSessionEnvironment(home_dir=Path("/fake/home"))

        result = find_project_dir(Path("/some/path"), env)
        assert result is None

    def test_returns_project_dir_if_exists(self) -> None:
        """Returns project directory path if it exists."""
        home = Path("/fake/home")
        cwd = Path("/some/path")
        encoded = encode_path_to_project_folder(cwd)
        projects_dir = home / ".claude" / "projects"
        project_dir = projects_dir / encoded

        # Need to include parent directories since we're not using files
        # (auto-create only runs for files)
        env = FakeSessionEnvironment(
            home_dir=home,
            directories={projects_dir, project_dir},
        )

        result = find_project_dir(cwd, env)
        assert result is not None
        assert result == project_dir
