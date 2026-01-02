"""Unit tests for issue_creation module."""

from pathlib import Path

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.learn.issue_creation import create_learn_issue


class TestCreateLearnIssue:
    """Tests for create_learn_issue function."""

    def test_creates_issue_with_correct_title(self) -> None:
        """Issue title follows 'Learn: {branch_name}' pattern."""
        fake_issues = FakeGitHubIssues()
        repo_root = Path("/repo")

        result = create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature-auth",
            pr_number=123,
            session_id="abc-123-def",
            synthesis="- Doc gap 1",
        )

        assert result.success
        assert len(fake_issues.created_issues) == 1
        title, _, _ = fake_issues.created_issues[0]
        assert title == "Learn: feature-auth"

    def test_creates_issue_with_erk_learn_label(self) -> None:
        """Issue has erk-learn label."""
        fake_issues = FakeGitHubIssues()
        repo_root = Path("/repo")

        create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature",
            pr_number=1,
            session_id="session",
            synthesis="gaps",
        )

        _, _, labels = fake_issues.created_issues[0]
        assert "erk-learn" in labels

    def test_ensures_label_exists(self) -> None:
        """Creates label if it doesn't exist."""
        fake_issues = FakeGitHubIssues()
        repo_root = Path("/repo")

        create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature",
            pr_number=1,
            session_id="session",
            synthesis="gaps",
        )

        assert "erk-learn" in fake_issues.labels

    def test_body_contains_metadata_header(self) -> None:
        """Issue body contains erk-learn-header metadata block."""
        fake_issues = FakeGitHubIssues()
        repo_root = Path("/repo")

        create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="my-feature",
            pr_number=456,
            session_id="session-xyz",
            synthesis="- Gap 1",
        )

        _, body, _ = fake_issues.created_issues[0]
        assert "<!-- erk-learn-header" in body
        assert "session_id: session-xyz" in body
        assert "branch: my-feature" in body
        assert "pr_number: 456" in body

    def test_body_contains_synthesis(self) -> None:
        """Issue body contains the synthesis content."""
        fake_issues = FakeGitHubIssues()
        repo_root = Path("/repo")

        create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature",
            pr_number=1,
            session_id="session",
            synthesis="- Missing docs for auth flow\n- Need examples for API",
        )

        _, body, _ = fake_issues.created_issues[0]
        assert "- Missing docs for auth flow" in body
        assert "- Need examples for API" in body

    def test_body_contains_source_context(self) -> None:
        """Issue body contains source context section."""
        fake_issues = FakeGitHubIssues()
        repo_root = Path("/repo")

        create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="fix-bug",
            pr_number=789,
            session_id="ses-123",
            synthesis="gaps",
        )

        _, body, _ = fake_issues.created_issues[0]
        assert "## Source Context" in body
        assert "**Branch**: fix-bug" in body
        assert "**PR**: #789" in body
        assert "**Session**: `ses-123`" in body

    def test_returns_issue_url_and_number(self) -> None:
        """Result contains issue URL and number."""
        fake_issues = FakeGitHubIssues(next_issue_number=42)
        repo_root = Path("/repo")

        result = create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature",
            pr_number=1,
            session_id="session",
            synthesis="gaps",
        )

        assert result.success
        assert result.issue_number == 42
        assert result.issue_url is not None
        assert "42" in result.issue_url

    def test_returns_error_on_label_failure(self) -> None:
        """Returns error when label creation fails."""

        # Create fake that will fail on label creation
        # We'll subclass to inject failure
        class FailingLabelGitHubIssues(FakeGitHubIssues):
            def ensure_label_exists(
                self,
                repo_root: Path,
                label: str,
                description: str,
                color: str,
            ) -> None:
                raise RuntimeError("Label API error")

        fake_issues = FailingLabelGitHubIssues()
        repo_root = Path("/repo")

        result = create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature",
            pr_number=1,
            session_id="session",
            synthesis="gaps",
        )

        assert not result.success
        assert result.issue_url is None
        assert result.issue_number is None
        assert "Failed to ensure label exists" in str(result.error)

    def test_returns_error_on_issue_creation_failure(self) -> None:
        """Returns error when issue creation fails."""

        class FailingCreateGitHubIssues(FakeGitHubIssues):
            def create_issue(self, repo_root: Path, title: str, body: str, labels: list[str]):
                raise RuntimeError("Issue API error")

        fake_issues = FailingCreateGitHubIssues()
        repo_root = Path("/repo")

        result = create_learn_issue(
            github_issues=fake_issues,
            repo_root=repo_root,
            branch_name="feature",
            pr_number=1,
            session_id="session",
            synthesis="gaps",
        )

        assert not result.success
        assert result.issue_url is None
        assert result.issue_number is None
        assert "Failed to create issue" in str(result.error)
