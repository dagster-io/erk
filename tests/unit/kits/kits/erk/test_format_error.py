"""Unit tests for format-error kit CLI command."""

import pytest
from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.format_error import (
    format_error,
    format_error_message,
)

# Test the utility function


def test_format_error_message_single_action() -> None:
    """Test error formatting with single action."""
    result = format_error_message(
        brief="No plan found",
        details="Could not find a valid implementation plan",
        actions=["Ensure plan is in conversation"],
    )

    assert "❌ Error: No plan found" in result
    assert "Details: Could not find a valid implementation plan" in result
    assert "Suggested action:" in result
    assert "  1. Ensure plan is in conversation" in result


def test_format_error_message_multiple_actions() -> None:
    """Test error formatting with multiple actions."""
    result = format_error_message(
        brief="Plan validation failed",
        details="Plan is too short and lacks structure",
        actions=[
            "Provide a more detailed plan",
            "Include specific tasks and steps",
            "Use headers and lists for structure",
        ],
    )

    assert "❌ Error: Plan validation failed" in result
    assert "Details: Plan is too short and lacks structure" in result
    assert "  1. Provide a more detailed plan" in result
    assert "  2. Include specific tasks and steps" in result
    assert "  3. Use headers and lists for structure" in result


def test_format_error_message_no_actions_raises() -> None:
    """Test error formatting fails with no actions."""
    with pytest.raises(ValueError, match="At least one action must be provided"):
        format_error_message(
            brief="Error occurred",
            details="Something went wrong",
            actions=[],
        )


def test_format_error_message_formatting() -> None:
    """Test error message has correct formatting structure."""
    result = format_error_message(
        brief="Test error",
        details="Test details",
        actions=["Action one", "Action two"],
    )

    lines = result.split("\n")
    assert lines[0] == "❌ Error: Test error"
    assert lines[1] == ""
    assert lines[2] == "Details: Test details"
    assert lines[3] == ""
    assert lines[4] == "Suggested actions:"  # plural for multiple actions
    assert lines[5] == "  1. Action one"
    assert lines[6] == "  2. Action two"


def test_format_error_message_long_text() -> None:
    """Test error formatting with long text content."""
    long_details = (
        "This is a very long error message that contains a lot of detail about "
        "what went wrong and why it happened."
    )
    long_action = (
        "This is a detailed action that explains exactly what the user should do "
        "to fix the problem."
    )

    result = format_error_message(
        brief="Long error message",
        details=long_details,
        actions=[long_action],
    )

    assert long_details in result
    assert long_action in result


def test_format_error_message_special_characters() -> None:
    """Test error formatting handles special characters."""
    result = format_error_message(
        brief="Special chars: $PATH & 'quotes'",
        details='Details with "quotes" and <brackets>',
        actions=["Action with | pipe and ; semicolon"],
    )

    assert "$PATH & 'quotes'" in result
    assert '"quotes" and <brackets>' in result
    assert "| pipe and ; semicolon" in result


# Test the CLI command


def test_cli_single_action() -> None:
    """Test CLI with single action."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "No plan found",
            "--details",
            "Could not find plan",
            "--action",
            "Add plan to conversation",
        ],
    )

    assert result.exit_code == 0
    assert "❌ Error: No plan found" in result.output
    assert "Details: Could not find plan" in result.output
    assert "  1. Add plan to conversation" in result.output


def test_cli_multiple_actions() -> None:
    """Test CLI with multiple actions."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Validation failed",
            "--details",
            "Plan is invalid",
            "--action",
            "Fix error 1",
            "--action",
            "Fix error 2",
            "--action",
            "Fix error 3",
        ],
    )

    assert result.exit_code == 0
    assert "  1. Fix error 1" in result.output
    assert "  2. Fix error 2" in result.output
    assert "  3. Fix error 3" in result.output


def test_cli_missing_brief() -> None:
    """Test CLI fails gracefully when brief is missing."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--details",
            "Details",
            "--action",
            "Action",
        ],
    )

    assert result.exit_code != 0


def test_cli_missing_details() -> None:
    """Test CLI fails gracefully when details is missing."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Brief",
            "--action",
            "Action",
        ],
    )

    assert result.exit_code != 0


def test_cli_missing_actions() -> None:
    """Test CLI fails gracefully when no actions provided."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Brief",
            "--details",
            "Details",
        ],
    )

    assert result.exit_code != 0


def test_cli_output_structure() -> None:
    """Test CLI output has expected structure."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Test",
            "--details",
            "Details",
            "--action",
            "Action",
        ],
    )

    assert result.exit_code == 0
    lines = result.output.strip().split("\n")

    # Check structure
    assert lines[0].startswith("❌ Error:")
    assert "Details:" in result.output
    assert "Suggested action:" in result.output
    assert "  1." in result.output


def test_cli_numbered_list_format() -> None:
    """Test CLI produces correctly numbered list."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Multiple errors",
            "--details",
            "Several issues found",
            "--action",
            "First",
            "--action",
            "Second",
            "--action",
            "Third",
            "--action",
            "Fourth",
            "--action",
            "Fifth",
        ],
    )

    assert result.exit_code == 0
    assert "  1. First" in result.output
    assert "  2. Second" in result.output
    assert "  3. Third" in result.output
    assert "  4. Fourth" in result.output
    assert "  5. Fifth" in result.output


def test_cli_unicode_content() -> None:
    """Test CLI handles unicode content correctly."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "错误",
            "--details",
            "详细信息",
            "--action",
            "操作步骤",
        ],
    )

    assert result.exit_code == 0
    assert "错误" in result.output
    assert "详细信息" in result.output
    assert "操作步骤" in result.output


def test_cli_whitespace_preservation() -> None:
    """Test CLI preserves intentional whitespace in content."""
    runner = CliRunner()
    result = runner.invoke(
        format_error,
        [
            "--brief",
            "Error with spacing",
            "--details",
            "Details  with  multiple  spaces",
            "--action",
            "Action  with  spaces",
        ],
    )

    assert result.exit_code == 0
    assert "Details  with  multiple  spaces" in result.output
    assert "Action  with  spaces" in result.output
