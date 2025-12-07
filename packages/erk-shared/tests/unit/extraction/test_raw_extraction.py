"""Tests for raw extraction orchestrator."""

import json
from pathlib import Path

from erk_shared.extraction.fake_session_environment import FakeSessionEnvironment, FileEntry
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
from erk_shared.extraction.session_discovery import encode_path_to_project_folder
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues.fake import FakeGitHubIssues


class TestCreateRawExtractionPlan:
    """Tests for create_raw_extraction_plan orchestrator."""

    def test_returns_error_when_project_dir_not_found(self, tmp_path: Path) -> None:
        """Returns error when project directory doesn't exist."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues()

        # Empty environment - no project dir
        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=Path("/fake/home"),
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            env=env,
        )

        assert result.success is False
        assert "No sessions found" in str(result.error)

    def test_returns_error_when_no_sessions_found(self, tmp_path: Path) -> None:
        """Returns error when no sessions exist."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues()

        # Create empty project directory
        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=home,
            directories={project_dir},  # Empty project dir
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            env=env,
        )

        assert result.success is False
        assert "No sessions found" in str(result.error)

    def test_returns_error_when_no_sessions_selected(self, tmp_path: Path) -> None:
        """Returns error when no sessions are selected."""
        git = FakeGit(
            current_branches={tmp_path: "main"},  # On trunk
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues()

        # Create project directory with session that won't be selected
        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded
        session_path = project_dir / "other.jsonl"

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",  # Not "other"
            home_dir=home,
            files={
                session_path: FileEntry(content="{}", mtime=1000.0),
            },
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            min_size=0,
            env=env,
        )

        assert result.success is False
        assert "No sessions" in str(result.error)

    def test_returns_error_when_username_not_authenticated(self, tmp_path: Path) -> None:
        """Returns error when GitHub username not available."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username=None)  # Not authenticated

        # Create project directory with session
        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded
        session_path = project_dir / "abc123.jsonl"

        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=home,
            files={
                session_path: FileEntry(
                    content="\n".join(json.dumps(e) for e in session_content),
                    mtime=1000.0,
                ),
            },
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            min_size=0,
            env=env,
        )

        assert result.success is False
        assert "Could not get GitHub username" in str(result.error)

    def test_creates_issue_and_comments_successfully(self, tmp_path: Path) -> None:
        """Successfully creates issue with session content comments."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username="testuser")

        # Create project directory with meaningful session
        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded
        session_path = project_dir / "abc123.jsonl"

        session_content = [
            {"type": "user", "message": {"content": "Hello world"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}},
            {"type": "user", "message": {"content": "Thank you"}},
        ]

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=home,
            files={
                session_path: FileEntry(
                    content="\n".join(json.dumps(e) for e in session_content),
                    mtime=1000.0,
                ),
            },
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            min_size=0,
            env=env,
        )

        assert result.success is True
        assert result.issue_url is not None
        assert result.issue_number == 1
        assert result.chunks >= 1
        assert "abc123" in result.sessions_processed
        assert result.error is None

        # Verify issue was created with correct labels
        assert len(github_issues.created_issues) == 1
        title, body, labels = github_issues.created_issues[0]
        assert "[erk-extraction]" in title
        assert "erk-plan" in labels
        assert "erk-extraction" in labels

        # Verify comments were added
        assert len(github_issues.added_comments) >= 1

    def test_uses_branch_name_in_issue_title(self, tmp_path: Path) -> None:
        """Branch name is included in issue title."""
        git = FakeGit(
            current_branches={tmp_path: "feature-awesome"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username="testuser")

        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded
        session_path = project_dir / "abc123.jsonl"

        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=home,
            files={
                session_path: FileEntry(
                    content="\n".join(json.dumps(e) for e in session_content),
                    mtime=1000.0,
                ),
            },
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            min_size=0,
            env=env,
        )

        assert result.success is True
        title, _, _ = github_issues.created_issues[0]
        assert "[erk-extraction]" in title
        assert "feature-awesome" in title

    def test_ensures_labels_exist(self, tmp_path: Path) -> None:
        """Required labels are ensured to exist."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username="testuser")

        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded
        session_path = project_dir / "abc123.jsonl"

        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=home,
            files={
                session_path: FileEntry(
                    content="\n".join(json.dumps(e) for e in session_content),
                    mtime=1000.0,
                ),
            },
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            min_size=0,
            env=env,
        )

        assert result.success is True
        label_names = {label[0] for label in github_issues.created_labels}
        assert "erk-plan" in label_names
        assert "erk-extraction" in label_names

    def test_issue_body_contains_metadata_only_and_plan_in_first_comment(
        self, tmp_path: Path
    ) -> None:
        """Issue body contains only metadata, plan is in first comment (Schema v2)."""
        git = FakeGit(
            current_branches={tmp_path: "feature-docs"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username="testuser")

        home = Path("/fake/home")
        encoded = encode_path_to_project_folder(tmp_path)
        project_dir = home / ".claude" / "projects" / encoded
        session_path = project_dir / "abc123.jsonl"

        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]

        env = FakeSessionEnvironment(
            session_context="session_id=abc123",
            home_dir=home,
            files={
                session_path: FileEntry(
                    content="\n".join(json.dumps(e) for e in session_content),
                    mtime=1000.0,
                ),
            },
        )

        result = create_raw_extraction_plan(
            github_issues=github_issues,
            git=git,
            repo_root=tmp_path,
            cwd=tmp_path,
            current_session_id="abc123",
            min_size=0,
            env=env,
        )

        assert result.success is True
        _, body, _ = github_issues.created_issues[0]

        # Issue body should contain ONLY metadata (Schema v2)
        assert "plan-header" in body
        assert "schema_version" in body
        # Plan content should NOT be in the issue body
        assert "## Implementation Steps" not in body

        # Verify plan content is in the first comment (plan-body block)
        assert len(github_issues.added_comments) >= 2  # Plan comment + session content
        first_comment = github_issues.added_comments[0][1]  # (issue_number, comment_body)
        assert "plan-body" in first_comment
        assert "## Implementation Steps" in first_comment
        assert "Category A" in first_comment
        assert "Category B" in first_comment
        assert "feature-docs" in first_comment  # Branch name interpolated
