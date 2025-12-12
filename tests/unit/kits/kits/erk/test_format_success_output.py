"""Unit tests for format-success-output kit CLI command."""

import json

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.format_success_output import (
    format_success_output,
)


def test_format_success_output_basic() -> None:
    """Test basic success output formatting."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "123", "--issue-url", "https://github.com/org/repo/issues/123"],
    )

    assert result.exit_code == 0
    assert "✅ GitHub issue created: #123" in result.output
    assert "https://github.com/org/repo/issues/123" in result.output


def test_format_success_output_contains_next_steps() -> None:
    """Test output contains all next steps commands."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "42", "--issue-url", "https://github.com/test/repo/issues/42"],
    )

    assert result.exit_code == 0
    assert "Next steps:" in result.output
    assert "gh issue view 42 --web" in result.output
    assert "erk implement 42" in result.output
    assert "erk implement 42 --dangerous" in result.output
    assert "erk implement 42 --yolo" in result.output
    assert "erk submit 42" in result.output
    assert "/erk:submit-plan" in result.output


def test_format_success_output_contains_json_metadata() -> None:
    """Test output contains valid JSON metadata footer."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "99", "--issue-url", "https://github.com/org/repo/issues/99"],
    )

    assert result.exit_code == 0
    assert "---" in result.output

    # Extract and validate JSON from output
    lines = result.output.strip().split("\n")
    json_line = lines[-1]  # JSON should be last line
    metadata = json.loads(json_line)

    assert metadata["issue_number"] == 99
    assert metadata["issue_url"] == "https://github.com/org/repo/issues/99"
    assert metadata["status"] == "created"


def test_format_success_output_url_escaping() -> None:
    """Test URL is preserved correctly (no escaping issues)."""
    runner = CliRunner()
    url = "https://github.com/dagster-io/erk/issues/1004"
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "1004", "--issue-url", url],
    )

    assert result.exit_code == 0
    assert url in result.output


def test_format_success_output_large_issue_number() -> None:
    """Test formatting works with large issue numbers."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "99999", "--issue-url", "https://github.com/test/repo/issues/99999"],
    )

    assert result.exit_code == 0
    assert "#99999" in result.output
    assert "gh issue view 99999 --web" in result.output
    assert "erk implement 99999" in result.output


def test_format_success_output_json_structure() -> None:
    """Test JSON metadata has correct structure and types."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "5", "--issue-url", "https://github.com/test/repo/issues/5"],
    )

    assert result.exit_code == 0

    # Extract JSON
    lines = result.output.strip().split("\n")
    json_line = lines[-1]
    metadata = json.loads(json_line)

    # Check structure
    assert "issue_number" in metadata
    assert "issue_url" in metadata
    assert "status" in metadata

    # Check types
    assert isinstance(metadata["issue_number"], int)
    assert isinstance(metadata["issue_url"], str)
    assert isinstance(metadata["status"], str)


def test_format_success_output_sections_order() -> None:
    """Test output sections appear in correct order."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "10", "--issue-url", "https://github.com/test/repo/issues/10"],
    )

    assert result.exit_code == 0
    output = result.output

    # Find positions of key sections
    success_pos = output.find("✅ GitHub issue created")
    url_pos = output.find("https://github.com")
    next_steps_pos = output.find("Next steps:")
    separator_pos = output.find("---")
    json_pos = output.find('{"issue_number"')

    # Verify order
    assert success_pos < url_pos
    assert url_pos < next_steps_pos
    assert next_steps_pos < separator_pos
    assert separator_pos < json_pos


def test_format_success_output_command_labels() -> None:
    """Test command descriptions are present."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "7", "--issue-url", "https://github.com/test/repo/issues/7"],
    )

    assert result.exit_code == 0
    assert "View Issue:" in result.output
    assert "Interactive:" in result.output
    assert "Dangerous Interactive:" in result.output
    assert "Dangerous, Non-Interactive, Auto-Submit:" in result.output
    assert "Submit to Queue:" in result.output


def test_format_success_output_missing_issue_number() -> None:
    """Test command fails gracefully when issue number is missing."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-url", "https://github.com/test/repo/issues/1"],
    )

    assert result.exit_code != 0


def test_format_success_output_missing_issue_url() -> None:
    """Test command fails gracefully when issue URL is missing."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "1"],
    )

    assert result.exit_code != 0
