"""Tests for plan_issues.py - Schema v2 plan issue creation and update."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment, IssueInfo
from erk_shared.github.metadata import format_plan_header_body
from erk_shared.github.plan_issues import (
    CreatePlanIssueResult,
    UpdatePlanResult,
    create_plan_issue,
    update_plan_issue_content,
)


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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type="extraction",
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=["session-abc", "session-def"],
            source_repo=None,
            objective_issue=None,
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
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix="[custom-suffix]",
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=["bug", "priority-high"],
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type="extraction",
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=[123, 456],
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
        )

        assert result.success is True
        # Metadata is in the issue body - verify body contains source info
        _, body, _ = fake_gh.created_issues[0]
        assert "source_plan_issues" in body

    def test_includes_source_repo_for_cross_repo_plans(self, tmp_path: Path) -> None:
        """Include source_repo in metadata for cross-repo plans."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Cross-Repo Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo="owner/impl-repo",
            objective_issue=None,
        )

        assert result.success is True
        # Metadata is in the issue body - verify body contains source_repo
        _, body, _ = fake_gh.created_issues[0]
        assert "source_repo:" in body
        assert "owner/impl-repo" in body
        # Schema version remains 2 (source_repo is just an optional field)
        assert "schema_version: '2'" in body

    def test_omits_source_repo_for_same_repo_plans(self, tmp_path: Path) -> None:
        """Omit source_repo for same-repo plans."""
        fake_gh = FakeGitHubIssues(username="testuser")
        plan_content = "# Same-Repo Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,  # No source_repo provided
            objective_issue=None,
        )

        assert result.success is True
        _, body, _ = fake_gh.created_issues[0]
        # source_repo should not appear in the body
        assert "source_repo:" not in body
        # Schema version is always 2
        assert "schema_version: '2'" in body


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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
        )

        assert result.success is False
        assert result.issue_number is None
        assert result.issue_url is None
        assert result.error is not None
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
        )

        assert result.success is False
        assert result.issue_number is None
        assert result.error is not None
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
        )

        assert result.success is False
        assert result.issue_number is None
        assert result.error is not None
        assert "Failed to create GitHub issue" in result.error


class TestCreatePlanIssuePartialSuccess:
    """Test partial success scenarios (issue created, comment failed)."""

    def test_reports_partial_success_when_comment_fails(self, tmp_path: Path) -> None:
        """Report partial success when issue created but comment fails."""

        class FailingCommentGitHubIssues(FakeGitHubIssues):
            def add_comment(self, repo_root: Path, number: int, body: str) -> int:
                # Issue 1 exists because create_issue was called
                raise RuntimeError("Comment too large")

        fake_gh = FailingCommentGitHubIssues(username="testuser")
        plan_content = "# My Plan\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
        )

        # Partial success: issue created but comment failed
        assert result.success is False
        assert result.issue_number == 1  # Issue was created
        assert result.issue_url is not None
        assert result.error is not None
        assert "created but failed to add plan comment" in result.error

    def test_partial_success_preserves_title(self, tmp_path: Path) -> None:
        """Preserve extracted title even on partial success."""

        class FailingCommentGitHubIssues(FakeGitHubIssues):
            def add_comment(self, repo_root: Path, number: int, body: str) -> int:
                raise RuntimeError("Network error")

        fake_gh = FailingCommentGitHubIssues(username="testuser")
        plan_content = "# Important Feature\n\nContent..."

        result = create_plan_issue(
            github_issues=fake_gh,
            repo_root=tmp_path,
            plan_content=plan_content,
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type="extraction",
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=["abc"],
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=["erk-plan", "bug"],  # erk-plan would be duplicate
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type="extraction",
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=["session-abc"],
            source_repo=None,
            objective_issue=None,
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
            title=None,
            plan_type=None,
            extra_labels=None,
            title_suffix=None,
            source_plan_issues=None,
            extraction_session_ids=None,
            source_repo=None,
            objective_issue=None,
        )

        assert result.success is True
        assert result.issue_number == 42

        # Verify commands reference issue 42, not 1
        _, updated_body = fake_gh.updated_bodies[0]
        assert "erk implement 42" in updated_body
        assert "erk implement 42 --dangerous" in updated_body
        assert "erk plan submit 42" in updated_body


class TestUpdatePlanIssueContent:
    """Tests for update_plan_issue_content function."""

    def test_updates_plan_content_successfully(self, tmp_path: Path) -> None:
        """Update plan content in existing issue."""
        # Create an issue body with plan-header containing plan_comment_id
        issue_body = format_plan_header_body(
            created_at="2025-01-01T00:00:00Z",
            created_by="testuser",
            plan_comment_id=1000,  # Comment ID to update
        )
        now = datetime.now(UTC)

        # Set up fake with pre-configured issue and comment
        fake_gh = FakeGitHubIssues(
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Plan [erk-plan]",
                    body=issue_body,
                    state="OPEN",
                    url="https://github.com/test/repo/issues/42",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                    author="testuser",
                )
            },
            comments_with_urls={
                42: [
                    IssueComment(
                        body="Original plan content",
                        url="https://github.com/test/repo/issues/42#issuecomment-1000",
                        id=1000,
                        author="testuser",
                    )
                ]
            },
        )

        result = update_plan_issue_content(
            github_issues=fake_gh,
            repo_root=tmp_path,
            issue_number=42,
            new_plan_content="# Updated Plan\n\n- Step 1\n- Step 2",
        )

        assert result.success is True
        assert result.issue_number == 42
        assert result.comment_id == 1000
        assert result.error is None

        # Verify comment was updated
        assert len(fake_gh.updated_comments) == 1
        comment_id, new_body = fake_gh.updated_comments[0]
        assert comment_id == 1000
        assert "Updated Plan" in new_body
        assert "Step 1" in new_body

    def test_fails_when_issue_not_found(self, tmp_path: Path) -> None:
        """Return error when issue doesn't exist."""
        fake_gh = FakeGitHubIssues()

        result = update_plan_issue_content(
            github_issues=fake_gh,
            repo_root=tmp_path,
            issue_number=999,
            new_plan_content="# New Plan",
        )

        assert result.success is False
        assert result.issue_number == 999
        assert result.comment_id is None
        assert result.error is not None
        assert "Failed to get issue #999" in result.error

    def test_fails_when_issue_has_no_plan_comment_id(self, tmp_path: Path) -> None:
        """Return error when issue has no plan_comment_id in plan-header."""
        # Create an issue body with plan-header but NO plan_comment_id
        issue_body = format_plan_header_body(
            created_at="2025-01-01T00:00:00Z",
            created_by="testuser",
            plan_comment_id=None,  # No comment ID
        )
        now = datetime.now(UTC)

        fake_gh = FakeGitHubIssues(
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Plan [erk-plan]",
                    body=issue_body,
                    state="OPEN",
                    url="https://github.com/test/repo/issues/42",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                    author="testuser",
                )
            }
        )

        result = update_plan_issue_content(
            github_issues=fake_gh,
            repo_root=tmp_path,
            issue_number=42,
            new_plan_content="# New Plan",
        )

        assert result.success is False
        assert result.issue_number == 42
        assert result.comment_id is None
        assert result.error is not None
        assert "does not have a plan_comment_id" in result.error

    def test_fails_when_issue_has_no_plan_header(self, tmp_path: Path) -> None:
        """Return error when issue has no plan-header block at all."""
        now = datetime.now(UTC)

        fake_gh = FakeGitHubIssues(
            issues={
                42: IssueInfo(
                    number=42,
                    title="Random Issue",
                    body="This is just a regular issue body without metadata.",
                    state="OPEN",
                    url="https://github.com/test/repo/issues/42",
                    labels=[],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                    author="testuser",
                )
            }
        )

        result = update_plan_issue_content(
            github_issues=fake_gh,
            repo_root=tmp_path,
            issue_number=42,
            new_plan_content="# New Plan",
        )

        assert result.success is False
        assert result.issue_number == 42
        assert result.error is not None
        assert "does not have a plan_comment_id" in result.error

    def test_fails_when_comment_update_fails(self, tmp_path: Path) -> None:
        """Return error when comment update fails."""
        issue_body = format_plan_header_body(
            created_at="2025-01-01T00:00:00Z",
            created_by="testuser",
            plan_comment_id=1000,
        )
        now = datetime.now(UTC)

        # Comment ID 1000 is not in comments_with_urls or added_comments,
        # so update_comment will raise RuntimeError
        fake_gh = FakeGitHubIssues(
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Plan [erk-plan]",
                    body=issue_body,
                    state="OPEN",
                    url="https://github.com/test/repo/issues/42",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                    author="testuser",
                )
            },
            # No comments configured - comment 1000 doesn't exist
        )

        result = update_plan_issue_content(
            github_issues=fake_gh,
            repo_root=tmp_path,
            issue_number=42,
            new_plan_content="# New Plan",
        )

        assert result.success is False
        assert result.issue_number == 42
        assert result.comment_id == 1000
        assert result.error is not None
        assert "Failed to update comment #1000" in result.error

    def test_strips_whitespace_from_plan_content(self, tmp_path: Path) -> None:
        """Strips leading/trailing whitespace from plan content."""
        issue_body = format_plan_header_body(
            created_at="2025-01-01T00:00:00Z",
            created_by="testuser",
            plan_comment_id=1000,
        )
        now = datetime.now(UTC)

        fake_gh = FakeGitHubIssues(
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Plan [erk-plan]",
                    body=issue_body,
                    state="OPEN",
                    url="https://github.com/test/repo/issues/42",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                    author="testuser",
                )
            },
            comments_with_urls={
                42: [
                    IssueComment(
                        body="Original",
                        url="https://github.com/test/repo/issues/42#issuecomment-1000",
                        id=1000,
                        author="testuser",
                    )
                ]
            },
        )

        result = update_plan_issue_content(
            github_issues=fake_gh,
            repo_root=tmp_path,
            issue_number=42,
            new_plan_content="\n\n  # Trimmed Plan  \n\n",
        )

        assert result.success is True
        # Verify the content was stripped
        _, new_body = fake_gh.updated_comments[0]
        # The plan-body block should contain the trimmed content
        assert "# Trimmed Plan" in new_body


class TestUpdatePlanResultDataclass:
    """Test UpdatePlanResult dataclass."""

    def test_result_is_frozen(self) -> None:
        """Verify result is immutable."""
        result = UpdatePlanResult(
            success=True,
            issue_number=42,
            comment_id=1000,
            error=None,
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]

    def test_result_fields(self) -> None:
        """Verify all fields are accessible."""
        result = UpdatePlanResult(
            success=False,
            issue_number=42,
            comment_id=1000,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.issue_number == 42
        assert result.comment_id == 1000
        assert result.error == "Something went wrong"
