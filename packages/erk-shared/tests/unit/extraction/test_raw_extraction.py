"""Tests for raw extraction orchestrator."""

import json
from pathlib import Path
from unittest.mock import patch

from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
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

        # Mock find_project_dir to return None
        with patch("erk_shared.extraction.raw_extraction.find_project_dir", return_value=None):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
            )

        assert result.success is False
        assert "Could not find Claude Code project directory" in str(result.error)

    def test_returns_error_when_no_sessions_found(self, tmp_path: Path) -> None:
        """Returns error when no sessions exist."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues()

        # Create empty project directory
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
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
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "other.jsonl").write_text("{}", encoding="utf-8")

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",  # Not "other"
                min_size=0,  # Don't filter by size
            )

        assert result.success is False
        assert "No sessions selected" in str(result.error)

    def test_returns_error_when_username_not_authenticated(self, tmp_path: Path) -> None:
        """Returns error when GitHub username not available."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username=None)  # Not authenticated

        # Create project directory with session
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]
        (project_dir / "abc123.jsonl").write_text(
            "\n".join(json.dumps(e) for e in session_content), encoding="utf-8"
        )

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
                min_size=0,  # Don't filter by size
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
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        session_content = [
            {"type": "user", "message": {"content": "Hello world"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there!"}]}},
            {"type": "user", "message": {"content": "Thank you"}},
        ]
        (project_dir / "abc123.jsonl").write_text(
            "\n".join(json.dumps(e) for e in session_content), encoding="utf-8"
        )

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
                min_size=0,  # Don't filter by size
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

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]
        (project_dir / "abc123.jsonl").write_text(
            "\n".join(json.dumps(e) for e in session_content), encoding="utf-8"
        )

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
                min_size=0,  # Don't filter by size
            )

        assert result.success is True
        title, _, _ = github_issues.created_issues[0]
        assert "feature-awesome" in title

    def test_ensures_labels_exist(self, tmp_path: Path) -> None:
        """Required labels are ensured to exist."""
        git = FakeGit(
            current_branches={tmp_path: "feature-x"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username="testuser")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]
        (project_dir / "abc123.jsonl").write_text(
            "\n".join(json.dumps(e) for e in session_content), encoding="utf-8"
        )

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
                min_size=0,  # Don't filter by size
            )

        assert result.success is True
        label_names = {label[0] for label in github_issues.created_labels}
        assert "erk-plan" in label_names
        assert "erk-extraction" in label_names

    def test_issue_body_contains_implementation_plan(self, tmp_path: Path) -> None:
        """Issue body contains actionable implementation steps."""
        git = FakeGit(
            current_branches={tmp_path: "feature-docs"},
            default_branches={tmp_path: "main"},
        )
        github_issues = FakeGitHubIssues(username="testuser")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        session_content = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi!"}]}},
            {"type": "user", "message": {"content": "Thanks"}},
        ]
        (project_dir / "abc123.jsonl").write_text(
            "\n".join(json.dumps(e) for e in session_content), encoding="utf-8"
        )

        patch_target = "erk_shared.extraction.raw_extraction.find_project_dir"
        with patch(patch_target, return_value=project_dir):
            result = create_raw_extraction_plan(
                github_issues=github_issues,
                git=git,
                repo_root=tmp_path,
                cwd=tmp_path,
                current_session_id="abc123",
                min_size=0,  # Don't filter by size
            )

        assert result.success is True
        _, body, _ = github_issues.created_issues[0]

        # Verify implementation plan is present
        assert "## Implementation Steps" in body
        assert "Category A" in body
        assert "Category B" in body
        assert "feature-docs" in body  # Branch name interpolated
