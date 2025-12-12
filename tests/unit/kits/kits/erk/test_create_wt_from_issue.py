"""Unit tests for create_wt_from_issue kit CLI command.

Tests worktree creation from GitHub issues with erk-plan label using fakes.
"""

from pathlib import Path

from erk_kits.data.kits.erk.scripts.erk.create_wt_from_issue import (
    WorktreeCreationSuccess,
    create_wt_from_issue_impl,
    has_erk_plan_label,
)
from erk_shared.github.metadata import MetadataBlock, render_metadata_block
from erk_shared.integrations.erk_wt import (
    FakeErkWtKit,
    IssueData,
    IssueParseResult,
    WorktreeCreationResult,
)


def _make_issue_body(content: str = "Implementation details") -> str:
    """Create a valid issue body with plan-header metadata block."""
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "test-user",
    }
    header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))
    return f"{header_block}\n\n# Plan\n\n{content}"


# ============================================================================
# 1. Helper Function Tests (Layer 3: Pure Unit Tests)
# ============================================================================


def test_has_erk_plan_label_true() -> None:
    """Test has_erk_plan_label returns True when label present."""
    labels = ["bug", "erk-plan", "enhancement"]
    assert has_erk_plan_label(labels) is True


def test_has_erk_plan_label_false() -> None:
    """Test has_erk_plan_label returns False when label missing."""
    labels = ["bug", "enhancement"]
    assert has_erk_plan_label(labels) is False


def test_has_erk_plan_label_no_labels() -> None:
    """Test has_erk_plan_label returns False when no labels."""
    labels = []
    assert has_erk_plan_label(labels) is False


# ============================================================================
# 2. Success Case Tests (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_create_from_issue_number_success(tmp_path: Path) -> None:
    """Test creating worktree from plain issue number."""
    issue_body = _make_issue_body()
    fake = FakeErkWtKit(
        parse_results={
            "123": IssueParseResult(
                success=True,
                issue_number=123,
                message="Successfully parsed issue number",
            )
        },
        issues={
            123: IssueData(
                number=123,
                title="Test Issue",
                body=issue_body,
                state="open",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
            )
        },
        worktree_result=WorktreeCreationResult(
            success=True,
            worktree_name="feature-branch",
            worktree_path=str(tmp_path / "feature-branch"),
            branch_name="issue-123-test",
        ),
    )

    success, result = create_wt_from_issue_impl("123", fake)

    assert success is True
    assert isinstance(result, WorktreeCreationSuccess)
    assert result.issue_number == 123
    assert result.worktree_name == "feature-branch"
    assert result.branch_name == "issue-123-test"

    # Verify mutations occurred
    assert len(fake.created_worktrees) == 1
    assert "# Plan" in fake.created_worktrees[0]
    assert len(fake.posted_comments) == 1
    assert fake.posted_comments[0] == (123, "feature-branch", "issue-123-test")


def test_create_from_github_url_success(tmp_path: Path) -> None:
    """Test creating worktree from full GitHub URL."""
    issue_body = _make_issue_body("Details here")
    fake = FakeErkWtKit(
        parse_results={
            "https://github.com/owner/repo/issues/456": IssueParseResult(
                success=True,
                issue_number=456,
                message="Successfully parsed GitHub URL",
            )
        },
        issues={
            456: IssueData(
                number=456,
                title="Feature Request",
                body=issue_body,
                state="open",
                url="https://github.com/owner/repo/issues/456",
                labels=["erk-plan", "enhancement"],
            )
        },
        worktree_result=WorktreeCreationResult(
            success=True,
            worktree_name="feature-request",
            worktree_path=str(tmp_path / "feature-request"),
            branch_name="issue-456-feature",
        ),
    )

    success, result = create_wt_from_issue_impl(
        "https://github.com/owner/repo/issues/456",
        fake,
    )

    assert success is True
    assert isinstance(result, WorktreeCreationSuccess)
    assert result.issue_number == 456
    assert result.issue_url == "https://github.com/owner/repo/issues/456"


# ============================================================================
# 3. Error Case Tests (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_create_fails_parse_invalid_reference() -> None:
    """Test failure when issue reference cannot be parsed."""
    fake = FakeErkWtKit(
        parse_results={
            "invalid": IssueParseResult(
                success=False,
                error="invalid_format",
                message="Not a valid issue reference",
            )
        }
    )

    success, result = create_wt_from_issue_impl("invalid", fake)

    assert success is False
    assert isinstance(result, str)
    assert "Failed to parse issue reference" in result


def test_create_fails_issue_not_found() -> None:
    """Test failure when issue doesn't exist on GitHub."""
    fake = FakeErkWtKit(
        parse_results={"999": IssueParseResult(success=True, issue_number=999)},
        issues={},  # Issue 999 not in dict
    )

    success, result = create_wt_from_issue_impl("999", fake)

    assert success is False
    assert isinstance(result, str)
    assert "Failed to fetch issue #999" in result


def test_create_fails_missing_erk_plan_label() -> None:
    """Test failure when issue doesn't have erk-plan label."""
    fake = FakeErkWtKit(
        parse_results={"123": IssueParseResult(success=True, issue_number=123)},
        issues={
            123: IssueData(
                number=123,
                title="Test Issue",
                body="# Plan",
                state="open",
                url="https://github.com/owner/repo/issues/123",
                labels=["bug", "enhancement"],  # Missing erk-plan
            )
        },
    )

    success, result = create_wt_from_issue_impl("123", fake)

    assert success is False
    assert isinstance(result, str)
    assert "does not have the 'erk-plan' label" in result
    assert "bug, enhancement" in result


def test_create_fails_empty_issue_body() -> None:
    """Test failure when issue has no body content."""
    fake = FakeErkWtKit(
        parse_results={"123": IssueParseResult(success=True, issue_number=123)},
        issues={
            123: IssueData(
                number=123,
                title="Test Issue",
                body="",  # Empty body
                state="open",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
            )
        },
    )

    success, result = create_wt_from_issue_impl("123", fake)

    assert success is False
    assert isinstance(result, str)
    assert "has no body content" in result


def test_create_fails_worktree_creation() -> None:
    """Test failure when erk create command fails."""
    fake = FakeErkWtKit(
        parse_results={"123": IssueParseResult(success=True, issue_number=123)},
        issues={
            123: IssueData(
                number=123,
                title="Test Issue",
                body="# Plan\n\nDetails",
                state="open",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
            )
        },
        worktree_result=WorktreeCreationResult(success=False),
    )

    success, result = create_wt_from_issue_impl("123", fake)

    assert success is False
    assert isinstance(result, str)
    assert "Failed to create worktree" in result


# ============================================================================
# 4. Edge Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_create_continues_on_comment_failure(tmp_path: Path) -> None:
    """Test that worktree creation succeeds even if comment posting fails."""
    issue_body = _make_issue_body()
    fake = FakeErkWtKit(
        parse_results={"123": IssueParseResult(success=True, issue_number=123)},
        issues={
            123: IssueData(
                number=123,
                title="Test Issue",
                body=issue_body,
                state="open",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
            )
        },
        worktree_result=WorktreeCreationResult(
            success=True,
            worktree_name="feature",
            worktree_path=str(tmp_path / "feature"),
            branch_name="issue-123",
        ),
        comment_success=False,  # Comment posting fails
    )

    success, result = create_wt_from_issue_impl("123", fake)

    # Should still succeed overall
    assert success is True
    assert isinstance(result, WorktreeCreationSuccess)


def test_has_erk_plan_label_case_sensitive() -> None:
    """Test that erk-plan label matching is case sensitive."""
    labels = ["ERK-PLAN", "Erk-Plan"]
    assert has_erk_plan_label(labels) is False

    labels = ["erk-plan"]
    assert has_erk_plan_label(labels) is True
