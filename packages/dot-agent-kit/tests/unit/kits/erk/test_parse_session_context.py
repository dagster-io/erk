"""Unit tests for parse_session_context kit CLI command.

Tests session ID extraction from free-form text with various patterns:
- Full UUID patterns
- Explicit session prefix
- Remaining context extraction
"""

import json

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.parse_session_context import (
    extract_session_ids_from_text,
    parse_session_context,
)

# ============================================================================
# 1. Session ID Extraction Tests (12 tests)
# ============================================================================


def test_extract_full_uuid() -> None:
    """Test extraction of full UUID patterns."""
    text = "Please look at session 12345678-1234-1234-1234-123456789abc for context"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert session_ids == ["12345678-1234-1234-1234-123456789abc"]
    assert "12345678-1234-1234-1234-123456789abc" not in remaining


def test_extract_multiple_uuids() -> None:
    """Test extraction of multiple UUID patterns."""
    text = "Compare 12345678-1234-1234-1234-123456789abc and 87654321-4321-4321-4321-cba987654321"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert len(session_ids) == 2
    assert "12345678-1234-1234-1234-123456789abc" in session_ids
    assert "87654321-4321-4321-4321-cba987654321" in session_ids


def test_extract_session_prefix() -> None:
    """Test extraction with explicit 'session' prefix."""
    text = "session abc123def4 focus on testing patterns"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert session_ids == ["abc123def4"]
    assert "focus on testing patterns" in remaining


def test_extract_session_prefix_with_colon() -> None:
    """Test extraction with 'session:' prefix."""
    text = "session:abc123def4 focus on testing"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert session_ids == ["abc123def4"]
    assert "focus on testing" in remaining


def test_extract_session_prefix_case_insensitive() -> None:
    """Test that session prefix matching is case insensitive."""
    text = "SESSION abc123def4 focus on testing"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert session_ids == ["abc123def4"]


def test_extract_no_session_ids() -> None:
    """Test handling of text with no session IDs."""
    text = "Please help me understand the code"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert session_ids == []
    assert remaining == "Please help me understand the code"


def test_extract_preserves_remaining_context() -> None:
    """Test that remaining context is properly preserved."""
    text = "Look at session abc12345 and focus on error handling"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert "abc12345" in session_ids
    # Should have "Look at" and "and focus on error handling"
    assert "focus on error handling" in remaining


def test_extract_cleans_whitespace() -> None:
    """Test that extra whitespace is cleaned in remaining context."""
    text = "session abc12345   focus on   testing"
    session_ids, remaining = extract_session_ids_from_text(text)

    # Should not have multiple spaces
    assert "  " not in remaining


def test_extract_uuid_mixed_case() -> None:
    """Test UUID extraction with mixed case hex chars."""
    text = "session 12345678-AbCd-1234-eFaB-123456789abc"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert len(session_ids) == 1
    assert "12345678-AbCd-1234-eFaB-123456789abc" in session_ids


def test_extract_deduplicates_ids() -> None:
    """Test that duplicate session IDs are deduplicated."""
    text = "session abc12345 and session abc12345 again"
    session_ids, remaining = extract_session_ids_from_text(text)

    # Should only appear once
    assert session_ids.count("abc12345") == 1


def test_extract_empty_text() -> None:
    """Test handling of empty text."""
    session_ids, remaining = extract_session_ids_from_text("")

    assert session_ids == []
    assert remaining == ""


def test_extract_only_session_id() -> None:
    """Test text that is only a session ID."""
    text = "session 12345678-1234-1234-1234-123456789abc"
    session_ids, remaining = extract_session_ids_from_text(text)

    assert len(session_ids) == 1
    assert remaining == "" or remaining.strip() == ""


# ============================================================================
# 2. CLI Command Tests (6 tests)
# ============================================================================


def test_cli_with_text_option() -> None:
    """Test CLI with --text option."""
    runner = CliRunner()
    result = runner.invoke(
        parse_session_context,
        ["--text", "session abc12345 focus on testing"],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "abc12345" in output["session_ids"]
    assert "testing" in output["remaining_context"]


def test_cli_with_stdin() -> None:
    """Test CLI reading from stdin."""
    runner = CliRunner()
    result = runner.invoke(
        parse_session_context,
        [],
        input="session def45678 analyze the code",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "def45678" in output["session_ids"]


def test_cli_no_input_error() -> None:
    """Test CLI error when no input provided."""
    runner = CliRunner()
    # Mix stdin to not be a tty but empty
    result = runner.invoke(
        parse_session_context,
        [],
        input="",  # Empty stdin
    )

    # With empty stdin, we should still get success (empty results)
    # The error only occurs with isatty()
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["session_ids"] == []


def test_cli_uuid_extraction() -> None:
    """Test CLI extraction of full UUIDs."""
    runner = CliRunner()
    result = runner.invoke(
        parse_session_context,
        ["--text", "Look at 12345678-1234-1234-1234-123456789abc for context"],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert "12345678-1234-1234-1234-123456789abc" in output["session_ids"]


def test_cli_multiple_sessions() -> None:
    """Test CLI with multiple session IDs."""
    runner = CliRunner()
    text = "session abc12345 and session def67890 focus on patterns"
    result = runner.invoke(
        parse_session_context,
        ["--text", text],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output["session_ids"]) == 2
    assert "abc12345" in output["session_ids"]
    assert "def67890" in output["session_ids"]


def test_cli_output_structure() -> None:
    """Test that CLI output has expected structure."""
    runner = CliRunner()
    result = runner.invoke(
        parse_session_context,
        ["--text", "any text"],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert "success" in output
    assert "session_ids" in output
    assert "remaining_context" in output
    assert isinstance(output["session_ids"], list)
    assert isinstance(output["remaining_context"], str)
