"""Tests for get-pr-commit-message kit CLI command."""

from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.get_pr_commit_message import (
    _parse_pr_body_for_commit,
)


class TestParsePrBodyForCommit:
    """Tests for PR body parsing logic."""

    def test_extracts_summary_before_separator(self) -> None:
        """Summary is extracted before --- separator."""
        body = "This is the summary\n\n---\n\nMetadata footer"
        result = _parse_pr_body_for_commit(body)
        assert result == "This is the summary"

    def test_preserves_markdown_in_summary(self) -> None:
        """Markdown formatting in summary is preserved."""
        body = "## Title\n\n- Item 1\n- Item 2\n\n---\n\nFooter"
        result = _parse_pr_body_for_commit(body)
        assert result == "## Title\n\n- Item 1\n- Item 2"

    def test_handles_no_separator(self) -> None:
        """Returns full body if no --- separator."""
        body = "Just a simple body with no separator"
        result = _parse_pr_body_for_commit(body)
        assert result == "Just a simple body with no separator"

    def test_handles_multiple_separators(self) -> None:
        """Only splits on first --- separator."""
        body = "Summary\n\n---\n\nMiddle\n\n---\n\nFooter"
        result = _parse_pr_body_for_commit(body)
        assert result == "Summary"

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace is stripped."""
        body = "  \n\nSummary content  \n\n---\n\nFooter"
        result = _parse_pr_body_for_commit(body)
        assert result == "Summary content"

    def test_empty_summary_returns_empty(self) -> None:
        """Empty summary before separator returns empty string."""
        body = "\n---\n\nOnly metadata"
        result = _parse_pr_body_for_commit(body)
        assert result == ""
