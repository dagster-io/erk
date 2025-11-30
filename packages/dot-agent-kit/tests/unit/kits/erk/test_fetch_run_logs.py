"""Unit tests for fetch_run_logs kit CLI command.

Tests parsing of GitHub Actions run references from both plain IDs and full URLs.
"""

import json

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.fetch_run_logs import (
    FetchError,
    _parse_run_reference,
)
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.fetch_run_logs import (
    fetch_run_logs as fetch_run_logs_command,
)

# ============================================================================
# 1. Plain Run ID Parsing Tests
# ============================================================================


def test_parse_plain_run_id_success() -> None:
    """Test parsing plain run ID."""
    run_id, error = _parse_run_reference("12345678")
    assert run_id == "12345678"
    assert error is None


def test_parse_plain_run_id_single_digit() -> None:
    """Test parsing single digit run ID."""
    run_id, error = _parse_run_reference("5")
    assert run_id == "5"
    assert error is None


def test_parse_plain_run_id_large() -> None:
    """Test parsing large run ID."""
    run_id, error = _parse_run_reference("99999999999")
    assert run_id == "99999999999"
    assert error is None


# ============================================================================
# 2. GitHub Actions URL Parsing Tests
# ============================================================================


def test_parse_github_url_success() -> None:
    """Test parsing full GitHub Actions URL."""
    run_id, error = _parse_run_reference("https://github.com/dagster-io/erk/actions/runs/12345678")
    assert run_id == "12345678"
    assert error is None


def test_parse_github_url_different_owner() -> None:
    """Test parsing GitHub Actions URL with different owner."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/actions/runs/987654321")
    assert run_id == "987654321"
    assert error is None


def test_parse_github_url_with_hyphens() -> None:
    """Test parsing GitHub Actions URL with hyphenated owner/repo names."""
    run_id, error = _parse_run_reference("https://github.com/some-org/my-repo/actions/runs/42")
    assert run_id == "42"
    assert error is None


def test_parse_github_url_with_query_params() -> None:
    """Test parsing GitHub Actions URL with query parameters."""
    run_id, error = _parse_run_reference(
        "https://github.com/owner/repo/actions/runs/100?foo=bar&baz=qux"
    )
    assert run_id == "100"
    assert error is None


def test_parse_github_url_with_fragment() -> None:
    """Test parsing GitHub Actions URL with fragment."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/actions/runs/200#step:1:2")
    assert run_id == "200"
    assert error is None


def test_parse_github_url_http_protocol() -> None:
    """Test parsing GitHub Actions URL with http:// protocol."""
    run_id, error = _parse_run_reference("http://github.com/owner/repo/actions/runs/50")
    assert run_id == "50"
    assert error is None


def test_parse_github_url_large_run_id() -> None:
    """Test parsing GitHub Actions URL with large run ID."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/actions/runs/888888888888")
    assert run_id == "888888888888"
    assert error is None


# ============================================================================
# 3. Invalid Input Tests
# ============================================================================


def test_parse_invalid_non_numeric() -> None:
    """Test rejection of non-numeric plain input."""
    run_id, error = _parse_run_reference("not-a-number")
    assert run_id is None
    assert error is not None
    assert "number or GitHub Actions URL" in error


def test_parse_invalid_empty_string() -> None:
    """Test rejection of empty string."""
    run_id, error = _parse_run_reference("")
    assert run_id is None
    assert error is not None


def test_parse_invalid_negative_number() -> None:
    """Test rejection of negative number."""
    run_id, error = _parse_run_reference("-123")
    assert run_id is None
    assert error is not None


def test_parse_invalid_malformed_url() -> None:
    """Test rejection of malformed GitHub URL (missing actions segment)."""
    run_id, error = _parse_run_reference("https://github.com/owner/runs/123")
    assert run_id is None
    assert error is not None


def test_parse_invalid_wrong_host() -> None:
    """Test rejection of non-GitHub URL."""
    run_id, error = _parse_run_reference("https://gitlab.com/owner/repo/actions/runs/123")
    assert run_id is None
    assert error is not None


def test_parse_invalid_missing_run_id() -> None:
    """Test rejection of URL without run ID."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/actions/runs/")
    assert run_id is None
    assert error is not None


def test_parse_invalid_issues_url() -> None:
    """Test rejection of issues URL (not actions/runs)."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/issues/123")
    assert run_id is None
    assert error is not None


def test_parse_invalid_pull_url() -> None:
    """Test rejection of pull request URL."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/pull/123")
    assert run_id is None
    assert error is not None


def test_parse_invalid_workflows_url_not_runs() -> None:
    """Test rejection of workflows URL (not actions/runs)."""
    run_id, error = _parse_run_reference("https://github.com/owner/repo/actions/workflows/ci.yml")
    assert run_id is None
    assert error is not None


# ============================================================================
# 4. CLI Command Tests (testing error handling without subprocess)
# ============================================================================


def test_cli_invalid_format_exit_code() -> None:
    """Test CLI command exits with error code on invalid input format."""
    runner = CliRunner()
    result = runner.invoke(fetch_run_logs_command, ["not-a-number"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_format"
    assert "message" in output


def test_cli_invalid_url_exit_code() -> None:
    """Test CLI command exits with error code on invalid URL."""
    runner = CliRunner()
    result = runner.invoke(
        fetch_run_logs_command,
        ["https://github.com/owner/repo/issues/123"],
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_format"


def test_cli_json_output_structure_error() -> None:
    """Test that JSON output has expected structure on error."""
    runner = CliRunner()
    result = runner.invoke(fetch_run_logs_command, ["invalid"])

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


# ============================================================================
# 5. FetchError Dataclass Tests
# ============================================================================


def test_fetch_error_basic_fields() -> None:
    """Test FetchError dataclass basic fields."""
    error = FetchError(
        success=False,
        error="not_found",
        message="Run not found",
    )
    assert error.success is False
    assert error.error == "not_found"
    assert error.message == "Run not found"
    assert error.status is None


def test_fetch_error_with_status() -> None:
    """Test FetchError dataclass with status field."""
    error = FetchError(
        success=False,
        error="in_progress",
        message="Run is in progress",
        status="in_progress",
    )
    assert error.success is False
    assert error.error == "in_progress"
    assert error.status == "in_progress"
