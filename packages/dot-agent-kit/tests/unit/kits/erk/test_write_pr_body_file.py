"""Unit tests for write_pr_body_file kit CLI command.

Tests writing content to files for gh CLI usage.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.scripts.erk.write_pr_body_file import (
    WriteSuccess,
    _write_pr_body_file_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.write_pr_body_file import (
    write_pr_body_file as write_pr_body_file_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_writes_content_to_file(tmp_path: Path) -> None:
    """Test that content is written to file."""
    content = "## Summary\n\nThis is the PR body."

    result = _write_pr_body_file_impl(tmp_path, content, "pr_body.md")

    assert isinstance(result, WriteSuccess)
    assert result.success is True
    assert result.file == "pr_body.md"

    # Verify file contents
    output_file = tmp_path / "pr_body.md"
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == content


def test_impl_handles_special_characters(tmp_path: Path) -> None:
    """Test that special characters are preserved in file."""
    content = '## Summary\n\n`code` and "quotes" and $variables'

    result = _write_pr_body_file_impl(tmp_path, content, "body.md")

    assert isinstance(result, WriteSuccess)
    output_file = tmp_path / "body.md"
    assert output_file.read_text(encoding="utf-8") == content


def test_impl_creates_parent_directories(tmp_path: Path) -> None:
    """Test that parent directories are created if needed."""
    content = "Test content"

    result = _write_pr_body_file_impl(tmp_path, content, "nested/dir/body.md")

    assert isinstance(result, WriteSuccess)
    output_file = tmp_path / "nested" / "dir" / "body.md"
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == content


def test_impl_overwrites_existing_file(tmp_path: Path) -> None:
    """Test that existing file is overwritten."""
    output_file = tmp_path / "existing.md"
    output_file.write_text("old content", encoding="utf-8")

    result = _write_pr_body_file_impl(tmp_path, "new content", "existing.md")

    assert isinstance(result, WriteSuccess)
    assert output_file.read_text(encoding="utf-8") == "new content"


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_writes_file(tmp_path: Path) -> None:
    """Test CLI writes content to file."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        write_pr_body_file_command,
        ["--content", "## Summary\n\nBody text", "--output", "pr_body.md"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["file"] == "pr_body.md"

    # Verify file was written
    assert (tmp_path / "pr_body.md").exists()


def test_cli_requires_options(tmp_path: Path) -> None:
    """Test that CLI requires both --content and --output."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    # Missing --output
    result = runner.invoke(
        write_pr_body_file_command,
        ["--content", "test"],
        obj=ctx,
    )
    assert result.exit_code != 0

    # Missing --content
    result = runner.invoke(
        write_pr_body_file_command,
        ["--output", "test.md"],
        obj=ctx,
    )
    assert result.exit_code != 0


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        write_pr_body_file_command,
        ["--content", "test content", "--output", "test.md"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "file" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["file"], str)
