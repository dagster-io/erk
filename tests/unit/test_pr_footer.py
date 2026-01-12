"""Unit tests for PR footer utilities."""

from erk_shared.github.pr_footer import (
    ClosingReference,
    build_pr_body_footer,
    extract_closing_reference,
    extract_footer_from_body,
)


class TestExtractFooterFromBody:
    """Tests for extract_footer_from_body."""

    def test_extracts_footer_after_horizontal_rule(self) -> None:
        """Test extracting footer content after --- delimiter."""
        body = "## Summary\n\nThis is a PR.\n---\n\nCloses #123\n\nCheckout instructions..."
        footer = extract_footer_from_body(body)
        assert footer == "\nCloses #123\n\nCheckout instructions..."

    def test_returns_none_when_no_delimiter(self) -> None:
        """Test returns None when no --- delimiter exists."""
        body = "## Summary\n\nThis is a PR with no footer."
        footer = extract_footer_from_body(body)
        assert footer is None

    def test_handles_multiple_delimiters(self) -> None:
        """Test handles multiple --- delimiters (uses last one)."""
        body = "First section\n---\nSecond section\n---\nActual footer"
        footer = extract_footer_from_body(body)
        assert footer == "Actual footer"

    def test_handles_empty_footer(self) -> None:
        """Test handles empty content after delimiter."""
        body = "## Summary\n---\n"
        footer = extract_footer_from_body(body)
        assert footer == ""

    def test_handles_empty_body(self) -> None:
        """Test returns None for empty body."""
        footer = extract_footer_from_body("")
        assert footer is None


class TestExtractClosingReference:
    """Tests for extract_closing_reference."""

    def test_extracts_same_repo_reference(self) -> None:
        """Test extracting Closes #123 pattern."""
        footer = "\nCloses #123\n\nTo checkout..."
        result = extract_closing_reference(footer)
        assert result == ClosingReference(issue_number=123, plans_repo=None)

    def test_extracts_cross_repo_reference(self) -> None:
        """Test extracting Closes owner/repo#123 pattern."""
        footer = "\nCloses dagster-io/plans#456\n\nTo checkout..."
        result = extract_closing_reference(footer)
        assert result == ClosingReference(issue_number=456, plans_repo="dagster-io/plans")

    def test_returns_none_when_no_reference(self) -> None:
        """Test returns None when no closing reference exists."""
        footer = "\nTo checkout this PR in a fresh worktree...\n"
        result = extract_closing_reference(footer)
        assert result is None

    def test_handles_closing_with_extra_whitespace(self) -> None:
        """Test handles extra whitespace after Closes."""
        footer = "Closes   #789"
        result = extract_closing_reference(footer)
        assert result == ClosingReference(issue_number=789, plans_repo=None)

    def test_handles_repo_with_dots(self) -> None:
        """Test handles repo names with dots."""
        footer = "Closes org/my.repo.name#100"
        result = extract_closing_reference(footer)
        assert result == ClosingReference(issue_number=100, plans_repo="org/my.repo.name")

    def test_handles_repo_with_hyphens(self) -> None:
        """Test handles owner and repo names with hyphens."""
        footer = "Closes my-org/my-repo#42"
        result = extract_closing_reference(footer)
        assert result == ClosingReference(issue_number=42, plans_repo="my-org/my-repo")

    def test_cross_repo_takes_precedence(self) -> None:
        """Test that cross-repo pattern is checked before same-repo."""
        # If both patterns exist, the cross-repo one should be found
        footer = "Closes org/repo#100"
        result = extract_closing_reference(footer)
        assert result is not None
        assert result.plans_repo == "org/repo"
        assert result.issue_number == 100


class TestBuildPrBodyFooter:
    """Tests for build_pr_body_footer."""

    def test_builds_footer_with_same_repo_issue(self) -> None:
        """Test building footer with same-repo issue reference."""
        footer = build_pr_body_footer(pr_number=42, issue_number=123, plans_repo=None)
        assert "Closes #123" in footer
        assert "erk pr checkout 42" in footer

    def test_builds_footer_with_cross_repo_issue(self) -> None:
        """Test building footer with cross-repo issue reference."""
        footer = build_pr_body_footer(pr_number=42, issue_number=456, plans_repo="dagster-io/plans")
        assert "Closes dagster-io/plans#456" in footer
        assert "erk pr checkout 42" in footer

    def test_builds_footer_without_issue(self) -> None:
        """Test building footer without issue reference."""
        footer = build_pr_body_footer(pr_number=42, issue_number=None, plans_repo=None)
        assert "Closes" not in footer
        assert "erk pr checkout 42" in footer


class TestClosingReference:
    """Tests for ClosingReference dataclass."""

    def test_same_repo_reference(self) -> None:
        """Test creating same-repo reference."""
        ref = ClosingReference(issue_number=123, plans_repo=None)
        assert ref.issue_number == 123
        assert ref.plans_repo is None

    def test_cross_repo_reference(self) -> None:
        """Test creating cross-repo reference."""
        ref = ClosingReference(issue_number=456, plans_repo="org/repo")
        assert ref.issue_number == 456
        assert ref.plans_repo == "org/repo"

    def test_equality(self) -> None:
        """Test equality comparison of frozen dataclass."""
        ref1 = ClosingReference(issue_number=123, plans_repo=None)
        ref2 = ClosingReference(issue_number=123, plans_repo=None)
        assert ref1 == ref2

    def test_inequality_on_issue_number(self) -> None:
        """Test inequality when issue numbers differ."""
        ref1 = ClosingReference(issue_number=123, plans_repo=None)
        ref2 = ClosingReference(issue_number=456, plans_repo=None)
        assert ref1 != ref2

    def test_inequality_on_plans_repo(self) -> None:
        """Test inequality when plans_repo differs."""
        ref1 = ClosingReference(issue_number=123, plans_repo=None)
        ref2 = ClosingReference(issue_number=123, plans_repo="org/repo")
        assert ref1 != ref2
