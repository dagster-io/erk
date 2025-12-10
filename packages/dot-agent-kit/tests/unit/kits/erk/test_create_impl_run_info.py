"""Unit tests for create_impl_run_info kit CLI command.

Tests creating run-info.json with workflow metadata.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.scripts.erk.create_impl_run_info import (
    CreateError,
    CreateSuccess,
    _create_impl_run_info_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.create_impl_run_info import (
    create_impl_run_info as create_impl_run_info_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_creates_valid_json(tmp_path: Path) -> None:
    """Test that valid JSON file is created with run info."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    result = _create_impl_run_info_impl(
        tmp_path,
        run_id="12345",
        run_url="https://github.com/owner/repo/actions/runs/12345",
        output_dir=".impl",
    )

    assert isinstance(result, CreateSuccess)
    assert result.success is True
    assert result.file == ".impl/run-info.json"

    # Verify file contents
    run_info_file = impl_dir / "run-info.json"
    assert run_info_file.exists()
    content = json.loads(run_info_file.read_text(encoding="utf-8"))
    assert content["run_id"] == "12345"
    assert content["run_url"] == "https://github.com/owner/repo/actions/runs/12345"


def test_impl_fails_missing_directory(tmp_path: Path) -> None:
    """Test error when output directory doesn't exist."""
    result = _create_impl_run_info_impl(
        tmp_path,
        run_id="12345",
        run_url="https://github.com/...",
        output_dir=".impl",  # Directory doesn't exist
    )

    assert isinstance(result, CreateError)
    assert result.success is False
    assert result.error == "directory_not_found"


def test_impl_handles_special_characters(tmp_path: Path) -> None:
    """Test that special characters are properly escaped in JSON."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    result = _create_impl_run_info_impl(
        tmp_path,
        run_id="run-with-special-chars-123",
        run_url='https://example.com/runs?param="value"',
        output_dir=".impl",
    )

    assert isinstance(result, CreateSuccess)

    # Verify JSON is valid and can be parsed
    run_info_file = impl_dir / "run-info.json"
    content = json.loads(run_info_file.read_text(encoding="utf-8"))
    assert content["run_url"] == 'https://example.com/runs?param="value"'


def test_impl_creates_in_nested_dir(tmp_path: Path) -> None:
    """Test creating run-info.json in nested directory."""
    nested_dir = tmp_path / "some" / "nested" / "dir"
    nested_dir.mkdir(parents=True)

    result = _create_impl_run_info_impl(
        tmp_path,
        run_id="99999",
        run_url="https://github.com/...",
        output_dir="some/nested/dir",
    )

    assert isinstance(result, CreateSuccess)
    assert (nested_dir / "run-info.json").exists()


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_creates_file(tmp_path: Path) -> None:
    """Test CLI creates run-info.json."""
    runner = CliRunner()
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://...", "--output-dir", ".impl"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["file"] == ".impl/run-info.json"


def test_cli_error_missing_dir(tmp_path: Path) -> None:
    """Test CLI exits with error when directory missing."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://...", "--output-dir", ".impl"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "directory_not_found"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://...", "--output-dir", ".impl"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "file" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["file"], str)
