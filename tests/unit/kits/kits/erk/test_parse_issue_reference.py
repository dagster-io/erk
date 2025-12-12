"""Unit tests for parse_issue_reference kit CLI command.

Tests parsing of GitHub issue references from both plain numbers and full URLs.
"""

import json

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.parse_issue_reference import (
    ParsedIssue,
    ParseError,
)
from erk_kits.data.kits.erk.scripts.erk.parse_issue_reference import (
    _parse_issue_reference_impl as parse_issue_reference,
)
from erk_kits.data.kits.erk.scripts.erk.parse_issue_reference import (
    parse_issue_reference as parse_issue_reference_command,
)

# ============================================================================
# 1. Plain Number Parsing Tests (4 tests)
# ============================================================================


def test_parse_plain_number_success() -> None:
    """Test parsing plain issue number."""
    result = parse_issue_reference("776")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 776


def test_parse_plain_number_single_digit() -> None:
    """Test parsing single digit issue number."""
    result = parse_issue_reference("5")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 5


def test_parse_plain_number_large() -> None:
    """Test parsing large issue number."""
    result = parse_issue_reference("99999")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 99999


def test_parse_plain_number_zero_fails() -> None:
    """Test that zero issue number is rejected."""
    result = parse_issue_reference("0")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_number"
    assert "positive" in result.message


# ============================================================================
# 2. GitHub URL Parsing Tests (8 tests)
# ============================================================================


def test_parse_github_url_success() -> None:
    """Test parsing full GitHub URL."""
    result = parse_issue_reference("https://github.com/dagster-io/erk/issues/776")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 776


def test_parse_github_url_different_owner() -> None:
    """Test parsing GitHub URL with different owner."""
    result = parse_issue_reference("https://github.com/owner/repo/issues/123")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 123


def test_parse_github_url_with_hyphens() -> None:
    """Test parsing GitHub URL with hyphenated owner/repo names."""
    result = parse_issue_reference("https://github.com/some-org/my-repo/issues/42")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 42


def test_parse_github_url_with_query_params() -> None:
    """Test parsing GitHub URL with query parameters."""
    result = parse_issue_reference("https://github.com/owner/repo/issues/100?foo=bar&baz=qux")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 100


def test_parse_github_url_with_fragment() -> None:
    """Test parsing GitHub URL with fragment."""
    result = parse_issue_reference("https://github.com/owner/repo/issues/200#issuecomment-123")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 200


def test_parse_github_url_http_protocol() -> None:
    """Test parsing GitHub URL with http:// protocol."""
    result = parse_issue_reference("http://github.com/owner/repo/issues/50")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 50


def test_parse_github_url_zero_issue_fails() -> None:
    """Test that GitHub URL with zero issue number is rejected."""
    result = parse_issue_reference("https://github.com/owner/repo/issues/0")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_number"
    assert "positive" in result.message


def test_parse_github_url_large_issue() -> None:
    """Test parsing GitHub URL with large issue number."""
    result = parse_issue_reference("https://github.com/owner/repo/issues/888888")
    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 888888


# ============================================================================
# 3. Invalid Input Tests (7 tests)
# ============================================================================


def test_parse_invalid_non_numeric() -> None:
    """Test rejection of non-numeric plain input."""
    result = parse_issue_reference("not-a-number")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"
    assert "number or GitHub URL" in result.message


def test_parse_invalid_empty_string() -> None:
    """Test rejection of empty string."""
    result = parse_issue_reference("")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"


def test_parse_invalid_negative_number() -> None:
    """Test rejection of negative number."""
    result = parse_issue_reference("-123")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"


def test_parse_invalid_malformed_url() -> None:
    """Test rejection of malformed GitHub URL."""
    result = parse_issue_reference("https://github.com/owner/issues/123")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"


def test_parse_invalid_wrong_host() -> None:
    """Test rejection of non-GitHub URL."""
    result = parse_issue_reference("https://gitlab.com/owner/repo/issues/123")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"


def test_parse_invalid_missing_issue_number() -> None:
    """Test rejection of URL without issue number."""
    result = parse_issue_reference("https://github.com/owner/repo/issues/")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"


def test_parse_invalid_pull_request_url() -> None:
    """Test rejection of pull request URL (not issue)."""
    result = parse_issue_reference("https://github.com/owner/repo/pull/123")
    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"


# ============================================================================
# 4. CLI Command Tests (5 tests)
# ============================================================================


def test_cli_success_plain_number() -> None:
    """Test CLI command with plain issue number."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["776"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 776


def test_cli_success_github_url() -> None:
    """Test CLI command with GitHub URL."""
    runner = CliRunner()
    result = runner.invoke(
        parse_issue_reference_command,
        ["https://github.com/dagster-io/erk/issues/776"],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 776


def test_cli_invalid_input_exit_code() -> None:
    """Test CLI command exits with error code on invalid input."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["not-a-number"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_format"


def test_cli_json_output_structure_success() -> None:
    """Test that JSON output has expected structure on success."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["123"])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)


def test_cli_json_output_structure_error() -> None:
    """Test that JSON output has expected structure on error."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["invalid"])

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)
