"""Unit tests for PR footer utilities."""

from erk_shared.gateway.github.pr_footer import (
    build_pr_body_footer,
    extract_footer_from_body,
)


class TestExtractFooterFromBody:
    """Tests for extract_footer_from_body."""

    def test_extracts_footer_after_horizontal_rule(self) -> None:
        """Test extracting footer content after --- delimiter."""
        body = "## Summary\n\nThis is a PR.\n---\n\nCheckout instructions..."
        footer = extract_footer_from_body(body)
        assert footer == "\nCheckout instructions..."

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


class TestBuildPrBodyFooter:
    """Tests for build_pr_body_footer."""

    def test_builds_footer_with_checkout_command(self) -> None:
        """Test building footer includes checkout command."""
        footer = build_pr_body_footer(42)
        assert "erk pr checkout 42" in footer
        assert "Closes" not in footer

    def test_includes_horizontal_rule(self) -> None:
        """Test footer includes horizontal rule separator."""
        footer = build_pr_body_footer(42)
        assert "---" in footer
