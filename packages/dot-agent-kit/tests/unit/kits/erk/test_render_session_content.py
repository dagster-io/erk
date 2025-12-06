"""Unit tests for render_session_content kit CLI command.

Tests rendering of session XML content as GitHub-ready comment bodies.
"""

import json

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.render_session_content import (
    render_session_content,
)

# ============================================================================
# 1. CLI Success Tests (6 tests)
# ============================================================================


def test_cli_renders_basic_content() -> None:
    """Test basic content rendering."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="<session>test content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["comment_bodies"]) == 1
    assert output["chunk_count"] == 1


def test_cli_includes_session_label() -> None:
    """Test that session label is included in output."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-label", "feature-branch"],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "feature-branch" in output["comment_bodies"][0]


def test_cli_includes_extraction_hints() -> None:
    """Test that extraction hints are included in output."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--extraction-hints", "error handling,test patterns"],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    # Check hints appear in comment body
    body = output["comment_bodies"][0]
    assert "error handling" in body
    assert "test patterns" in body


def test_cli_output_structure() -> None:
    """Test that output has expected structure."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert "success" in output
    assert "comment_bodies" in output
    assert "chunk_count" in output
    assert isinstance(output["comment_bodies"], list)
    assert isinstance(output["chunk_count"], int)


def test_cli_preserves_xml_content() -> None:
    """Test that XML content is preserved in output."""
    xml_content = "<session><message>Test message</message></session>"
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input=xml_content,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    # XML content should be wrapped in code fence
    assert "Test message" in output["comment_bodies"][0]


def test_cli_combined_options() -> None:
    """Test CLI with both session label and hints."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-label", "my-branch", "--extraction-hints", "patterns,testing"],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    body = output["comment_bodies"][0]
    assert "my-branch" in body
    assert "patterns" in body


# ============================================================================
# 2. Error Handling Tests (3 tests)
# ============================================================================


def test_cli_empty_input_error() -> None:
    """Test error when input is empty."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="",
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Empty input" in output["error"]


def test_cli_whitespace_only_error() -> None:
    """Test error when input is only whitespace."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="   \n  \n  ",
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_cli_empty_hints_handled() -> None:
    """Test that empty hints string is handled gracefully."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--extraction-hints", ""],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True


# ============================================================================
# 3. Content Format Tests (3 tests)
# ============================================================================


def test_cli_wraps_in_metadata_block() -> None:
    """Test that output is wrapped in metadata block structure."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    body = output["comment_bodies"][0]

    # Check for metadata block markers
    assert "<!-- erk:metadata-block:session-content -->" in body
    assert "<!-- /erk:metadata-block:session-content -->" in body


def test_cli_uses_details_summary() -> None:
    """Test that output uses HTML details/summary for collapsibility."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    body = output["comment_bodies"][0]

    assert "<details>" in body
    assert "</details>" in body
    assert "<summary>" in body


def test_cli_uses_xml_code_fence() -> None:
    """Test that content is in XML code fence."""
    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [],
        input="<session>content</session>",
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    body = output["comment_bodies"][0]

    assert "```xml" in body
