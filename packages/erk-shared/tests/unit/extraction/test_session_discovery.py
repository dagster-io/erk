"""Tests for session discovery module."""

from pathlib import Path
from unittest.mock import patch

from erk_shared.extraction.session_discovery import (
    discover_sessions,
    encode_path_to_project_folder,
    find_project_dir,
    get_branch_context,
)
from erk_shared.git.fake import FakeGit


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

    def test_discovers_sessions_in_project_dir(self, tmp_path: Path) -> None:
        """Discovers session JSONL files in project directory."""
        # Create test session files
        (tmp_path / "session1.jsonl").write_text("{}", encoding="utf-8")
        (tmp_path / "session2.jsonl").write_text("{}", encoding="utf-8")

        result = discover_sessions(
            project_dir=tmp_path,
            current_session_id=None,
            min_size=0,
            limit=10,
        )

        assert len(result) == 2
        session_ids = {s.session_id for s in result}
        assert session_ids == {"session1", "session2"}

    def test_excludes_agent_logs(self, tmp_path: Path) -> None:
        """Agent log files are excluded from results."""
        (tmp_path / "session1.jsonl").write_text("{}", encoding="utf-8")
        (tmp_path / "agent-abc123.jsonl").write_text("{}", encoding="utf-8")

        result = discover_sessions(
            project_dir=tmp_path,
            current_session_id=None,
            min_size=0,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].session_id == "session1"

    def test_excludes_non_jsonl_files(self, tmp_path: Path) -> None:
        """Non-JSONL files are excluded from results."""
        (tmp_path / "session1.jsonl").write_text("{}", encoding="utf-8")
        (tmp_path / "config.json").write_text("{}", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")

        result = discover_sessions(
            project_dir=tmp_path,
            current_session_id=None,
            min_size=0,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].session_id == "session1"

    def test_filters_by_min_size(self, tmp_path: Path) -> None:
        """Sessions below min_size are filtered out."""
        (tmp_path / "small.jsonl").write_text("{}", encoding="utf-8")  # ~2 bytes
        (tmp_path / "large.jsonl").write_text("x" * 1000, encoding="utf-8")  # 1000 bytes

        result = discover_sessions(
            project_dir=tmp_path,
            current_session_id=None,
            min_size=500,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].session_id == "large"

    def test_respects_limit(self, tmp_path: Path) -> None:
        """Only returns up to limit sessions."""
        for i in range(5):
            (tmp_path / f"session{i}.jsonl").write_text("{}", encoding="utf-8")

        result = discover_sessions(
            project_dir=tmp_path,
            current_session_id=None,
            min_size=0,
            limit=3,
        )

        assert len(result) == 3

    def test_marks_current_session(self, tmp_path: Path) -> None:
        """Current session is marked with is_current=True."""
        (tmp_path / "session1.jsonl").write_text("{}", encoding="utf-8")
        (tmp_path / "session2.jsonl").write_text("{}", encoding="utf-8")

        result = discover_sessions(
            project_dir=tmp_path,
            current_session_id="session1",
            min_size=0,
            limit=10,
        )

        session1 = next(s for s in result if s.session_id == "session1")
        session2 = next(s for s in result if s.session_id == "session2")

        assert session1.is_current is True
        assert session2.is_current is False

    def test_returns_empty_for_nonexistent_dir(self, tmp_path: Path) -> None:
        """Returns empty list for non-existent project directory."""
        nonexistent = tmp_path / "nonexistent"

        result = discover_sessions(
            project_dir=nonexistent,
            current_session_id=None,
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

    def test_returns_none_if_projects_dir_not_exists(self, tmp_path: Path) -> None:
        """Returns None if ~/.claude/projects/ doesn't exist."""
        # Mock Path.home() to return tmp_path
        with patch("erk_shared.extraction.session_discovery.Path.home", return_value=tmp_path):
            result = find_project_dir(Path("/some/path"))
            assert result is None

    def test_returns_project_dir_if_exists(self, tmp_path: Path) -> None:
        """Returns project directory path if it exists."""
        # Create the projects directory structure
        projects_dir = tmp_path / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        # Create the encoded project directory
        encoded = "-some-path"
        (projects_dir / encoded).mkdir()

        with patch("erk_shared.extraction.session_discovery.Path.home", return_value=tmp_path):
            result = find_project_dir(Path("/some/path"))
            assert result is not None
            assert result == projects_dir / encoded
