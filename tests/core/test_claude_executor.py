"""Tests for claude_executor module."""

import json
from pathlib import Path

from erk.core.claude_executor import RealClaudeExecutor
from erk.core.output_filter import extract_pr_metadata_from_text


def test_parse_stream_json_line_extracts_pr_metadata_from_string_content() -> None:
    """Test that _parse_stream_json_line extracts PR metadata from string tool_result content."""
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    # Simulate a user message with tool_result containing string content (raw JSON)
    pr_metadata_json = json.dumps(
        {
            "success": True,
            "pr_number": 123,
            "pr_url": "https://github.com/owner/repo/pull/123",
            "pr_title": "Fix bug",
            "issue_number": 456,
        }
    )
    line = json.dumps(
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": pr_metadata_json}]},
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["pr_url"] == "https://github.com/owner/repo/pull/123"
    assert result["pr_number"] == 123
    assert result["pr_title"] == "Fix bug"
    assert result["issue_number"] == 456


def test_parse_stream_json_line_extracts_pr_metadata_from_list_content() -> None:
    """Test that _parse_stream_json_line extracts PR metadata from list tool_result content.

    This is the stream-json format where tool_result.content is a list of text items:
    {"type": "tool_result", "content": [{"type": "text", "text": "...json..."}]}
    """
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    # Simulate a user message with tool_result containing list content
    # This is how Bash tool results come back in stream-json format
    pr_metadata_json = json.dumps(
        {
            "success": True,
            "pr_number": 789,
            "pr_url": "https://github.com/owner/repo/pull/789",
            "pr_title": "Add feature",
            "graphite_url": "https://app.graphite.dev/...",
            "branch_name": "feature-branch",
            "issue_number": 101,
        }
    )
    line = json.dumps(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [{"type": "text", "text": pr_metadata_json}],
                    }
                ]
            },
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["pr_url"] == "https://github.com/owner/repo/pull/789"
    assert result["pr_number"] == 789
    assert result["pr_title"] == "Add feature"
    assert result["issue_number"] == 101


def test_parse_stream_json_line_handles_list_content_without_pr_metadata() -> None:
    """Test that list content without PR metadata returns None values."""
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    # Simulate a tool_result with non-JSON text content
    line = json.dumps(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [{"type": "text", "text": "Exit code: 0\nDone!"}],
                    }
                ]
            },
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["pr_url"] is None
    assert result["pr_number"] is None


def test_parse_stream_json_line_handles_empty_list_content() -> None:
    """Test that empty list content is handled gracefully."""
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    line = json.dumps(
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": []}]},
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["pr_url"] is None


def test_parse_stream_json_line_extracts_result_num_turns() -> None:
    """Test that _parse_stream_json_line extracts num_turns from type: result messages."""
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    # Simulate a result message with num_turns: 0 (hook blocking scenario)
    line = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 478,
            "num_turns": 0,
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["num_turns"] == 0
    assert result["is_error"] is False


def test_parse_stream_json_line_extracts_result_with_positive_turns() -> None:
    """Test that _parse_stream_json_line extracts num_turns from successful result."""
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    # Simulate a successful result with positive num_turns
    line = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 5000,
            "num_turns": 5,
            "result": "Command completed successfully",
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["num_turns"] == 5
    assert result["is_error"] is False
    assert result["result_text"] == "Command completed successfully"


def test_parse_stream_json_line_extracts_result_error() -> None:
    """Test that _parse_stream_json_line handles error results."""
    executor = RealClaudeExecutor()
    worktree_path = Path("/test/repo")
    command = "/gt:pr-submit"

    # Simulate an error result
    line = json.dumps(
        {
            "type": "result",
            "subtype": "error",
            "is_error": True,
            "duration_ms": 100,
            "num_turns": 1,
            "result": "An error occurred",
        }
    )

    result = executor._parse_stream_json_line(line, worktree_path, command)

    assert result is not None
    assert result["num_turns"] == 1
    assert result["is_error"] is True
    assert result["result_text"] == "An error occurred"


def test_extract_pr_metadata_from_text_extracts_all_fields() -> None:
    """Test that extract_pr_metadata_from_text extracts PR info from agent output."""
    # Simulate typical agent text output with title
    text = """## Branch Submission Complete

### What Was Done

✓ Created commit with AI-generated message
✓ Submitted branch to Graphite
✓ Updated PR #1311: Fix metadata extraction from text
✓ Linked to issue #1308 (will auto-close on merge)

### View PR

https://github.com/dagster-io/erk/pull/1311"""

    result = extract_pr_metadata_from_text(text)

    assert result["pr_number"] == 1311
    assert result["pr_title"] == "Fix metadata extraction from text"
    assert result["pr_url"] == "https://github.com/dagster-io/erk/pull/1311"
    assert result["issue_number"] == 1308


def test_extract_pr_metadata_from_text_extracts_graphite_url() -> None:
    """Test that Graphite URL is extracted when GitHub URL not present."""
    text = """Branch submitted!

View PR: https://app.graphite.com/github/pr/owner/repo/456"""

    result = extract_pr_metadata_from_text(text)

    assert result["pr_number"] == 456
    assert result["pr_url"] == "https://app.graphite.com/github/pr/owner/repo/456"


def test_extract_pr_metadata_from_text_handles_closes_pattern() -> None:
    """Test that 'Closes #N' pattern is recognized for issue linking."""
    text = "Created PR #100: Add feature. Closes #200"

    result = extract_pr_metadata_from_text(text)

    assert result["pr_number"] == 100
    assert result["issue_number"] == 200


# =============================================================================
# Extensive tests for extract_pr_metadata_from_text
# =============================================================================


class TestExtractPrMetadataFromText:
    """Comprehensive tests for PR metadata text extraction."""

    # -------------------------------------------------------------------------
    # PR Number + Title extraction patterns
    # -------------------------------------------------------------------------

    def test_colon_separator_format(self) -> None:
        """Test 'PR #123: Title' format."""
        text = "✓ Updated PR #1311: Fix metadata extraction"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 1311
        assert result["pr_title"] == "Fix metadata extraction"

    def test_dash_separator_format(self) -> None:
        """Test '#123 - Title' format (common agent variation)."""
        text = "✅ **PR Updated**: #1311 - Fix metadata extraction"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 1311
        assert result["pr_title"] == "Fix metadata extraction"

    def test_quoted_title_double_quotes(self) -> None:
        """Test '#123 - "Title"' format with double quotes."""
        text = '#1311 - "Extend PR submission metadata"'
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 1311
        assert result["pr_title"] == "Extend PR submission metadata"

    def test_quoted_title_single_quotes(self) -> None:
        """Test "#123 - 'Title'" format with single quotes."""
        text = "#1311 - 'Extend PR submission metadata'"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 1311
        assert result["pr_title"] == "Extend PR submission metadata"

    def test_markdown_bold_format(self) -> None:
        """Test '**PR Updated**: #123 - Title' markdown format."""
        text = '✅ **PR Updated**: #456 - "Add new feature for users"'
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 456
        assert result["pr_title"] == "Add new feature for users"

    def test_pr_number_only_no_title(self) -> None:
        """Test fallback when title not present."""
        text = "Created PR #789 successfully"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 789
        assert result["pr_title"] is None

    def test_title_with_special_characters(self) -> None:
        """Test title extraction with special characters."""
        text = "#100: Fix bug in auth (BREAKING CHANGE)"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 100
        assert result["pr_title"] == "Fix bug in auth (BREAKING CHANGE)"

    def test_title_stops_at_newline(self) -> None:
        """Test that title extraction stops at newline."""
        text = "#100: First line title\nThis is not part of title"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 100
        assert result["pr_title"] == "First line title"

    # -------------------------------------------------------------------------
    # URL extraction patterns
    # -------------------------------------------------------------------------

    def test_github_url_extraction(self) -> None:
        """Test GitHub PR URL extraction."""
        text = "View at https://github.com/owner/repo/pull/123"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_url"] == "https://github.com/owner/repo/pull/123"
        assert result["pr_number"] == 123

    def test_github_url_with_org_name(self) -> None:
        """Test GitHub URL with organization name."""
        text = "PR: https://github.com/dagster-io/erk/pull/1311"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_url"] == "https://github.com/dagster-io/erk/pull/1311"
        assert result["pr_number"] == 1311

    def test_graphite_url_extraction(self) -> None:
        """Test Graphite URL extraction as fallback."""
        text = "View PR: https://app.graphite.com/github/pr/owner/repo/456"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_url"] == "https://app.graphite.com/github/pr/owner/repo/456"
        assert result["pr_number"] == 456

    def test_github_url_preferred_over_graphite(self) -> None:
        """Test that GitHub URL is preferred when both present."""
        text = """View on GitHub: https://github.com/owner/repo/pull/123
View on Graphite: https://app.graphite.com/github/pr/owner/repo/123"""
        result = extract_pr_metadata_from_text(text)

        assert result["pr_url"] == "https://github.com/owner/repo/pull/123"

    def test_pr_number_from_url_when_not_in_text(self) -> None:
        """Test PR number extraction from URL when not elsewhere in text."""
        text = "Created: https://github.com/owner/repo/pull/999"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 999
        assert result["pr_url"] == "https://github.com/owner/repo/pull/999"

    # -------------------------------------------------------------------------
    # Issue number extraction patterns
    # -------------------------------------------------------------------------

    def test_issue_pattern_lowercase(self) -> None:
        """Test 'issue #N' pattern (lowercase)."""
        text = "Linked to issue #456"
        result = extract_pr_metadata_from_text(text)

        assert result["issue_number"] == 456

    def test_issue_pattern_mixed_case(self) -> None:
        """Test 'Issue #N' pattern (mixed case)."""
        text = "Linked to Issue #456"
        result = extract_pr_metadata_from_text(text)

        assert result["issue_number"] == 456

    def test_closes_pattern_lowercase(self) -> None:
        """Test 'closes #N' pattern."""
        text = "This PR closes #789"
        result = extract_pr_metadata_from_text(text)

        assert result["issue_number"] == 789

    def test_closes_pattern_uppercase(self) -> None:
        """Test 'Closes #N' pattern."""
        text = "Closes #789"
        result = extract_pr_metadata_from_text(text)

        assert result["issue_number"] == 789

    def test_issue_pattern_preferred_over_closes(self) -> None:
        """Test that 'issue #N' pattern is checked first."""
        text = "Linked to issue #100. Closes #200"
        result = extract_pr_metadata_from_text(text)

        # 'issue #N' pattern should match first
        assert result["issue_number"] == 100

    def test_issue_with_auto_close_context(self) -> None:
        """Test issue extraction with auto-close context."""
        text = "✓ Linked to issue #1308 (will auto-close on merge)"
        result = extract_pr_metadata_from_text(text)

        assert result["issue_number"] == 1308

    # -------------------------------------------------------------------------
    # Real-world agent output formats
    # -------------------------------------------------------------------------

    def test_full_agent_output_format_v1(self) -> None:
        """Test extraction from full agent output (template format)."""
        text = """## Branch Submission Complete

### What Was Done

✓ Created commit with AI-generated message
✓ Submitted branch to Graphite
✓ Updated PR #1311: Fix metadata extraction from text
✓ Linked to issue #1308 (will auto-close on merge)
✓ Posted PR link to issue #1308

### View PR

https://github.com/dagster-io/erk/pull/1311"""

        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 1311
        assert result["pr_title"] == "Fix metadata extraction from text"
        assert result["pr_url"] == "https://github.com/dagster-io/erk/pull/1311"
        assert result["issue_number"] == 1308

    def test_full_agent_output_format_v2(self) -> None:
        """Test extraction from agent output (variation format)."""
        text = """## Results

✅ **PR Updated**: #1311 - "Extend PR submission metadata to include title"

✅ **Changes Applied**:
- Squashed 2 commits into 1
- Linked to issue #1308 (will auto-close on merge)

🔗 **View PR**: https://app.graphite.com/github/pr/dagster-io/erk/1311"""

        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 1311
        assert result["pr_title"] == "Extend PR submission metadata to include title"
        assert result["pr_url"] == "https://app.graphite.com/github/pr/dagster-io/erk/1311"
        assert result["issue_number"] == 1308

    def test_minimal_success_output(self) -> None:
        """Test extraction from minimal success output."""
        text = "PR #42: Quick fix\nhttps://github.com/o/r/pull/42"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 42
        assert result["pr_title"] == "Quick fix"
        assert result["pr_url"] == "https://github.com/o/r/pull/42"

    # -------------------------------------------------------------------------
    # Edge cases and error handling
    # -------------------------------------------------------------------------

    def test_empty_string(self) -> None:
        """Test with empty string input."""
        result = extract_pr_metadata_from_text("")

        assert result["pr_number"] is None
        assert result["pr_title"] is None
        assert result["pr_url"] is None
        assert result["issue_number"] is None

    def test_no_pr_info(self) -> None:
        """Test with text containing no PR information."""
        text = "This is just some random text without any PR info."
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] is None
        assert result["pr_title"] is None
        assert result["pr_url"] is None
        assert result["issue_number"] is None

    def test_non_string_input(self) -> None:
        """Test with non-string input returns empty result."""
        result = extract_pr_metadata_from_text(None)  # type: ignore[arg-type] -- intentionally passing None to test defensive behavior

        assert result["pr_number"] is None
        assert result["pr_title"] is None
        assert result["pr_url"] is None
        assert result["issue_number"] is None

    def test_multiple_pr_numbers_first_wins(self) -> None:
        """Test that first PR number with title wins."""
        text = "#100: First PR\n#200: Second PR"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 100
        assert result["pr_title"] == "First PR"

    def test_url_only_no_text_pr_number(self) -> None:
        """Test extraction when only URL provides PR number."""
        text = "View: https://github.com/owner/repo/pull/555"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 555
        assert result["pr_url"] == "https://github.com/owner/repo/pull/555"
        assert result["pr_title"] is None

    def test_whitespace_handling(self) -> None:
        """Test that whitespace in title is handled correctly."""
        text = "#123:   Title with   extra   spaces  "
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 123
        # Leading/trailing whitespace stripped
        assert result["pr_title"] == "Title with   extra   spaces"

    def test_large_pr_numbers(self) -> None:
        """Test with large PR numbers."""
        text = "#99999: Large PR number\nhttps://github.com/o/r/pull/99999"
        result = extract_pr_metadata_from_text(text)

        assert result["pr_number"] == 99999
        assert result["pr_title"] == "Large PR number"
