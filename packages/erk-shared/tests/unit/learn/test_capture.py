"""Unit tests for capture module (orchestrator)."""

import json
from pathlib import Path

import pytest

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.capture import (
    _encode_worktree_path,
    _find_session_file,
    capture_for_learn,
)
from erk_shared.prompt_executor.fake import FakePromptExecutor


class TestEncodeWorktreePath:
    """Tests for _encode_worktree_path helper."""

    def test_encodes_absolute_path(self) -> None:
        """Absolute path is encoded with dashes."""
        path = Path("/Users/foo/repo")
        result = _encode_worktree_path(path)
        assert result == "-Users-foo-repo"

    def test_encodes_nested_path(self) -> None:
        """Deeply nested path works correctly."""
        path = Path("/Users/schrockn/.erk/repos/erk/worktrees/feature-branch")
        result = _encode_worktree_path(path)
        assert result == "-Users-schrockn-.erk-repos-erk-worktrees-feature-branch"


class TestFindSessionFile:
    """Tests for _find_session_file helper."""

    def test_returns_none_when_projects_folder_missing(self, tmp_path: Path) -> None:
        """Returns None when ~/.claude/projects folder doesn't exist."""
        # Use a path that won't match any real Claude projects folder
        result = _find_session_file("abc-123", tmp_path / "nonexistent")
        assert result is None


class TestCaptureForLearn:
    """Tests for capture_for_learn orchestrator."""

    def test_returns_none_when_no_impl_folder(self, tmp_path: Path) -> None:
        """Returns None when .impl/ folder doesn't exist."""
        fake_issues = FakeGitHubIssues()
        fake_executor = FakePromptExecutor()

        result = capture_for_learn(
            worktree_path=tmp_path,
            branch_name="feature",
            pr_number=1,
            github_issues=fake_issues,
            prompt_executor=fake_executor,
        )

        assert result is None

    def test_returns_none_when_no_run_state(self, tmp_path: Path) -> None:
        """Returns None when local-run-state.json doesn't exist."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        fake_issues = FakeGitHubIssues()
        fake_executor = FakePromptExecutor()

        result = capture_for_learn(
            worktree_path=tmp_path,
            branch_name="feature",
            pr_number=1,
            github_issues=fake_issues,
            prompt_executor=fake_executor,
        )

        assert result is None

    def test_returns_none_when_no_session_id(self, tmp_path: Path) -> None:
        """Returns None when run state has no session_id."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        # Create run state without session_id
        run_state = {
            "last_event": "ended",
            "timestamp": "2024-01-01T00:00:00Z",
            "session_id": None,
            "user": "testuser",
        }
        (impl_dir / "local-run-state.json").write_text(json.dumps(run_state), encoding="utf-8")

        fake_issues = FakeGitHubIssues()
        fake_executor = FakePromptExecutor()

        result = capture_for_learn(
            worktree_path=tmp_path,
            branch_name="feature",
            pr_number=1,
            github_issues=fake_issues,
            prompt_executor=fake_executor,
        )

        assert result is None

    def test_returns_error_when_session_file_not_found(self, tmp_path: Path) -> None:
        """Returns error when session file doesn't exist."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        # Create run state with session_id
        run_state = {
            "last_event": "ended",
            "timestamp": "2024-01-01T00:00:00Z",
            "session_id": "nonexistent-session-id",
            "user": "testuser",
        }
        (impl_dir / "local-run-state.json").write_text(json.dumps(run_state), encoding="utf-8")

        fake_issues = FakeGitHubIssues()
        fake_executor = FakePromptExecutor()

        result = capture_for_learn(
            worktree_path=tmp_path,
            branch_name="feature",
            pr_number=1,
            github_issues=fake_issues,
            prompt_executor=fake_executor,
        )

        assert result is not None
        assert not result.success
        assert "Session file not found" in str(result.error)

    @pytest.fixture
    def worktree_with_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Create a worktree with .impl/ and mock session file."""
        # Create .impl/ folder with run state
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        session_id = "test-session-123"
        run_state = {
            "last_event": "ended",
            "timestamp": "2024-01-01T00:00:00Z",
            "session_id": session_id,
            "user": "testuser",
        }
        (impl_dir / "local-run-state.json").write_text(json.dumps(run_state), encoding="utf-8")

        # Create mock ~/.claude/projects/{encoded-path}/ with session file
        encoded_path = str(tmp_path).replace("/", "-")
        mock_claude_projects = tmp_path / ".mock-claude" / "projects"
        project_folder = mock_claude_projects / encoded_path
        project_folder.mkdir(parents=True)

        session_content = (
            '{"type":"user","message":"hello"}\n{"type":"assistant","message":"world"}'
        )
        (project_folder / f"{session_id}.jsonl").write_text(session_content, encoding="utf-8")

        # Patch Path.home() to use our mock
        def mock_home():
            return tmp_path / ".mock-claude" / ".."

        # Actually, we need a different approach - patch the parent of projects
        # Let's create the structure properly
        real_mock_home = tmp_path / ".mock-home"
        claude_projects = real_mock_home / ".claude" / "projects"
        real_project_folder = claude_projects / encoded_path
        real_project_folder.mkdir(parents=True)
        (real_project_folder / f"{session_id}.jsonl").write_text(session_content, encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: real_mock_home)

        return tmp_path, session_id

    def test_full_capture_flow(self, worktree_with_session: tuple[Path, str]) -> None:
        """Full capture flow creates issue successfully."""
        worktree_path, session_id = worktree_with_session

        fake_issues = FakeGitHubIssues()
        # Configure executor to return XML for batch, then synthesis
        fake_executor = FakePromptExecutor(output="<user>hello</user>")

        # We need to handle multiple calls - first for XML conversion, then for synthesis
        # FakePromptExecutor returns the same output for all calls, which is fine for this test

        result = capture_for_learn(
            worktree_path=worktree_path,
            branch_name="feature-test",
            pr_number=42,
            github_issues=fake_issues,
            prompt_executor=fake_executor,
        )

        assert result is not None
        assert result.success
        assert result.issue_number is not None
        assert result.issue_url is not None

        # Verify issue was created
        assert len(fake_issues.created_issues) == 1
        title, body, labels = fake_issues.created_issues[0]
        assert "Learn: feature-test" == title
        assert "erk-learn" in labels
        assert session_id in body

    def test_returns_error_on_xml_conversion_failure(
        self, worktree_with_session: tuple[Path, str]
    ) -> None:
        """Returns error when XML conversion fails."""
        worktree_path, _ = worktree_with_session

        fake_issues = FakeGitHubIssues()
        fake_executor = FakePromptExecutor(should_fail=True, error="LLM API error")

        result = capture_for_learn(
            worktree_path=worktree_path,
            branch_name="feature",
            pr_number=1,
            github_issues=fake_issues,
            prompt_executor=fake_executor,
        )

        assert result is not None
        assert not result.success
        assert "Failed to convert session to XML" in str(result.error)
