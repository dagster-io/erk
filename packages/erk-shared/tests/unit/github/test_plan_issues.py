"""Tests for plan_issues.py - Schema v2 plan issue creation."""

from pathlib import Path

import pytest

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.plan_issues import CreatePlanIssueResult, create_plan_issue


class TestCreatePlanIssueSuccess:
    """Test successful plan issue creation scenarios."""

    def test_creates_standard_plan_issue(self, tmp_path: Path) -> None:
        """Create a standard plan issue with minimal options."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Feature Plan\n\nImplementation steps..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is True
        assert result.issue_number == 1
        assert result.issue_url is not None
        assert result.title == "My Feature Plan"
        assert result.error is None

        # Verify issue was created with correct title and labels
        assert len(fake_gh.created_issues) == 1
        title, body, labels = fake_gh.created_issues[0]
        assert title == "My Feature Plan [erk-plan]"
        assert labels == ["erk-plan"]

        # Verify plan content was added as comment
        assert len(fake_gh.added_comments) == 1
        issue_num, comment, _comment_id = fake_gh.added_comments[0]
        assert issue_num == 1
        assert "My Feature Plan" in comment
        assert "Implementation steps" in comment

    def test_creates_extraction_plan_issue(self, tmp_path: Path) -> None:
        """Create an extraction plan issue with extraction-specific labels."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Extraction Plan: main\n\nAnalysis..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            plan_type="extraction",
            extraction_session_ids=["session-abc", "session-def"],
        )

        assert result.success is True
        assert result.title == "Extraction Plan: main"

        # Verify labels include both erk-plan and erk-extraction
        title, body, labels = fake_gh.created_issues[0]
        assert title == "Extraction Plan: main [erk-extraction]"
        assert "erk-plan" in labels
        assert "erk-extraction" in labels

        # Verify both labels were created
        assert fake_gh.labels == {"erk-plan", "erk-extraction"}

    def test_uses_provided_title(self, tmp_path: Path) -> None:
        """Use provided title instead of extracting from H1."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Wrong Title\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            title="Correct Title",
        )

        assert result.success is True
        assert result.title == "Correct Title"
        title, _, _ = fake_gh.created_issues[0]
        assert title == "Correct Title [erk-plan]"

    def test_uses_custom_title_suffix(self, tmp_path: Path) -> None:
        """Use custom title suffix."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            title_suffix="[custom-suffix]",
        )

        assert result.success is True
        title, _, _ = fake_gh.created_issues[0]
        assert title == "My Plan [custom-suffix]"

    def test_adds_extra_labels(self, tmp_path: Path) -> None:
        """Add extra labels beyond erk-plan."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            extra_labels=["bug", "priority-high"],
        )

        assert result.success is True
        _, _, labels = fake_gh.created_issues[0]
        assert labels == ["erk-plan", "bug", "priority-high"]

    def test_includes_source_plan_issues(self, tmp_path: Path) -> None:
        """Include source_plan_issues in metadata."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Extraction Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            plan_type="extraction",
            source_plan_issues=[123, 456],
        )

        assert result.success is True
        # Metadata is in the issue body - verify body contains source info
        _, body, _ = fake_gh.created_issues[0]
        assert "source_plan_issues" in body


class TestCreatePlanIssueTitleExtraction:
    """Test title extraction from various plan formats."""

    def test_extracts_h1_title(self, tmp_path: Path) -> None:
        """Extract title from H1 heading."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Feature: Add Auth\n\nDetails..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.title == "Feature: Add Auth"

    def test_strips_plan_prefix(self, tmp_path: Path) -> None:
        """Strip common plan prefixes from title."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Plan: Add Feature X\n\nDetails..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.title == "Add Feature X"

    def test_strips_implementation_plan_prefix(self, tmp_path: Path) -> None:
        """Strip 'Implementation Plan:' prefix from title."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Implementation Plan: Refactor Y\n\nDetails..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.title == "Refactor Y"


class TestCreatePlanIssueErrors:
    """Test error handling scenarios."""

    def test_fails_when_not_authenticated(self, tmp_path: Path) -> None:
        """Fail when GitHub username cannot be retrieved."""
        fake_gh = FakeGitHubIssues(username=None)
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is False
        assert result.issue_number is None
        assert result.issue_url is None
        assert "not authenticated" in result.error.lower()

    def test_fails_on_label_creation_error(self, tmp_path: Path) -> None:
        """Fail when label creation fails."""

        class FailingLabelGitHubIssues(FakeGitHubIssues):
            def ensure_label_exists(
                self, repo_root: Path, label: str, description: str, color: str
            ) -> None:
                raise RuntimeError("Permission denied")

        fake_gh = FailingLabelGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is False
        assert result.issue_number is None
        assert "Failed to ensure labels exist" in result.error

    def test_fails_on_issue_creation_error(self, tmp_path: Path) -> None:
        """Fail when issue creation fails."""

        class FailingIssueGitHubIssues(FakeGitHubIssues):
            def create_issue(self, repo_root: Path, title: str, body: str, labels: list[str]):
                raise RuntimeError("API rate limit exceeded")

        fake_gh = FailingIssueGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is False
        assert result.issue_number is None
        assert "Failed to create GitHub issue" in result.error


class TestCreatePlanIssuePartialSuccess:
    """Test partial success scenarios (issue created, comment failed)."""

    def test_reports_partial_success_when_comment_fails(self, tmp_path: Path) -> None:
        """Report partial success when issue created but comment fails."""

        class FailingCommentGitHubIssues(FakeGitHubIssues):
            def add_comment(self, repo_root: Path, number: int, body: str) -> None:
                # Issue 1 exists because create_issue was called
                raise RuntimeError("Comment too large")

        fake_gh = FailingCommentGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        # Partial success: issue created but comment failed
        assert result.success is False
        assert result.issue_number == 1  # Issue was created
        assert result.issue_url is not None
        assert "created but failed to add plan comment" in result.error

    def test_partial_success_preserves_title(self, tmp_path: Path) -> None:
        """Preserve extracted title even on partial success."""

        class FailingCommentGitHubIssues(FakeGitHubIssues):
            def add_comment(self, repo_root: Path, number: int, body: str) -> None:
                raise RuntimeError("Network error")

        fake_gh = FailingCommentGitHubIssues(username="testuser")
        plan_content = "# Important Feature\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is False
        assert result.title == "Important Feature"


class TestCreatePlanIssueLabelManagement:
    """Test label creation and management."""

    def test_creates_erk_plan_label_if_missing(self, tmp_path: Path) -> None:
        """Create erk-plan label if it doesn't exist."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is True
        assert "erk-plan" in fake_gh.labels
        # Verify label was created with correct color
        assert len(fake_gh.created_labels) >= 1
        label_name, desc, color = fake_gh.created_labels[0]
        assert label_name == "erk-plan"
        assert color == "0E8A16"

    def test_creates_both_labels_for_extraction(self, tmp_path: Path) -> None:
        """Create both erk-plan and erk-extraction labels for extraction plans."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Extraction Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            plan_type="extraction",
            extraction_session_ids=["abc"],
        )

        assert result.success is True
        assert "erk-plan" in fake_gh.labels
        assert "erk-extraction" in fake_gh.labels

    def test_does_not_create_existing_labels(self, tmp_path: Path) -> None:
        """Don't create labels that already exist."""
        fake_gh = FakeGitHubIssues(
            username="testuser",
            labels={"erk-plan"},  # Already exists
        )
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is True
        # Label should not have been re-created
        assert len(fake_gh.created_labels) == 0

    def test_deduplicates_extra_labels(self, tmp_path: Path) -> None:
        """Don't duplicate labels if extra_labels includes erk-plan."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            extra_labels=["erk-plan", "bug"],  # erk-plan would be duplicate
        )

        assert result.success is True
        _, _, labels = fake_gh.created_issues[0]
        # Should not have duplicate erk-plan
        assert labels.count("erk-plan") == 1
        assert "bug" in labels


class TestCreatePlanIssueResultDataclass:
    """Test CreatePlanIssueResult dataclass."""

    def test_result_is_frozen(self) -> None:
        """Verify result is immutable."""
        result = CreatePlanIssueResult(
            success=True,
            issue_number=1,
            issue_url="https://example.com/1",
            title="Test",
            error=None,
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_result_fields(self) -> None:
        """Verify all fields are accessible."""
        result = CreatePlanIssueResult(
            success=False,
            issue_number=42,
            issue_url="https://github.com/test/repo/issues/42",
            title="My Title",
            error="Something went wrong",
        )

        assert result.success is False
        assert result.issue_number == 42
        assert result.issue_url == "https://github.com/test/repo/issues/42"
        assert result.title == "My Title"
        assert result.error == "Something went wrong"


class TestCreatePlanIssueCommandsSection:
    """Test that commands section is added correctly."""

    def test_standard_plan_includes_commands_section(self, tmp_path: Path) -> None:
        """Standard plans should include commands section with correct issue number."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# My Feature Plan\n\nImplementation steps..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is True
        assert result.issue_number == 1

        # Verify issue body was updated with commands section
        assert len(fake_gh.updated_bodies) == 1
        issue_num, updated_body = fake_gh.updated_bodies[0]
        assert issue_num == 1

        # Check for commands section with correct issue number
        assert "## Commands" in updated_body
        assert "erk implement 1" in updated_body
        assert "erk implement 1 --dangerous" in updated_body
        assert "erk plan submit 1" in updated_body

    def test_extraction_plan_does_not_include_commands_section(self, tmp_path: Path) -> None:
        """Extraction plans should NOT include commands section."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Extraction Plan\n\nAnalysis..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            plan_type="extraction",
            extraction_session_ids=["session-abc"],
        )

        assert result.success is True
        assert result.issue_number == 1

        # Verify issue body was updated but without commands section
        assert len(fake_gh.updated_bodies) == 1
        issue_num, updated_body = fake_gh.updated_bodies[0]
        assert issue_num == 1

        # Commands section should NOT be present
        assert "## Commands" not in updated_body
        assert "erk implement" not in updated_body

    def test_commands_section_uses_correct_issue_number(self, tmp_path: Path) -> None:
        """Commands section should reference the actual issue number."""
        fake_gh = FakeGitHubIssues(username="testuser", next_issue_number=42)
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
        )

        assert result.success is True
        assert result.issue_number == 42

        # Verify commands reference issue 42, not 1
        _, updated_body = fake_gh.updated_bodies[0]
        assert "erk implement 42" in updated_body
        assert "erk implement 42 --dangerous" in updated_body
        assert "erk plan submit 42" in updated_body
