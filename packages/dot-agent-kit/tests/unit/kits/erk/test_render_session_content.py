"""Unit tests for render-session-content kit CLI command."""

import json
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.render_session_content import (
    render_session_content,
)


def test_render_session_content_basic(tmp_path: Path) -> None:
    """Test basic rendering of small session content."""
    session_content = "<session>test content</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-file", str(session_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["chunk_count"] == 1
    assert len(output["blocks"]) == 1
    assert session_content in output["blocks"][0]
    assert "<!-- erk:metadata-block:session-content -->" in output["blocks"][0]


def test_render_session_content_with_label(tmp_path: Path) -> None:
    """Test rendering with session label."""
    session_content = "<session>test</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [
            "--session-file",
            str(session_file),
            "--session-label",
            "fix-auth-bug",
        ],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert "fix-auth-bug" in output["blocks"][0]


def test_render_session_content_with_hints(tmp_path: Path) -> None:
    """Test rendering with extraction hints."""
    session_content = "<session>test</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [
            "--session-file",
            str(session_file),
            "--extraction-hints",
            "Error handling patterns,Test fixture setup",
        ],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert "**Extraction Hints:**" in output["blocks"][0]
    assert "- Error handling patterns" in output["blocks"][0]
    assert "- Test fixture setup" in output["blocks"][0]


def test_render_session_content_with_label_and_hints(tmp_path: Path) -> None:
    """Test rendering with both label and hints."""
    session_content = "<session>test</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [
            "--session-file",
            str(session_file),
            "--session-label",
            "my-feature",
            "--extraction-hints",
            "Hint one,Hint two",
        ],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert "my-feature" in output["blocks"][0]
    assert "- Hint one" in output["blocks"][0]
    assert "- Hint two" in output["blocks"][0]


def test_render_session_content_output_format(tmp_path: Path) -> None:
    """Test that output is valid JSON with expected structure."""
    session_content = "<session>content</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-file", str(session_file)],
    )

    assert result.exit_code == 0

    # Verify output is valid JSON
    output = json.loads(result.output)

    # Verify expected keys exist
    assert "success" in output
    assert "blocks" in output
    assert "chunk_count" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["blocks"], list)
    assert isinstance(output["chunk_count"], int)


def test_render_session_content_handles_unicode(tmp_path: Path) -> None:
    """Test that unicode content is handled correctly."""
    session_content = "<session>测试内容 🔥 emoji content</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-file", str(session_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert "测试内容" in output["blocks"][0]
    assert "🔥" in output["blocks"][0]


def test_render_session_content_file_not_found(tmp_path: Path) -> None:
    """Test error when session file does not exist."""
    nonexistent = tmp_path / "nonexistent.xml"

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-file", str(nonexistent)],
    )

    # Click should fail because path doesn't exist
    assert result.exit_code != 0


def test_render_session_content_whitespace_hints(tmp_path: Path) -> None:
    """Test that hints with extra whitespace are trimmed."""
    session_content = "<session>test</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        [
            "--session-file",
            str(session_file),
            "--extraction-hints",
            "  Hint one  ,  Hint two  ",
        ],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Hints should be trimmed
    assert "- Hint one" in output["blocks"][0]
    assert "- Hint two" in output["blocks"][0]


def test_render_session_content_includes_metadata_markers(tmp_path: Path) -> None:
    """Test that output includes proper metadata block markers."""
    session_content = "<session>test</session>"
    session_file = tmp_path / "session.xml"
    session_file.write_text(session_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        render_session_content,
        ["--session-file", str(session_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    block = output["blocks"][0]

    # Check metadata block structure
    assert "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->" in block
    assert "<!-- erk:metadata-block:session-content -->" in block
    assert "<!-- /erk:metadata-block:session-content -->" in block
    assert "<details>" in block
    assert "</details>" in block
    assert "```xml" in block
