"""Unit tests for create_impl_run_info kit CLI command.

Tests creation of .impl/run-info.json with workflow metadata.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.create_impl_run_info import (
    RunInfoCreated,
    RunInfoError,
    _create_impl_run_info_impl,
)
from erk_kits.data.kits.erk.scripts.erk.create_impl_run_info import (
    create_impl_run_info as create_impl_run_info_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_success(tmp_path: Path) -> None:
    """Test successful creation when .impl directory exists."""
    # Create .impl directory
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    result = _create_impl_run_info_impl(
        tmp_path, run_id="12345", run_url="https://github.com/owner/repo/actions/runs/12345"
    )

    assert isinstance(result, RunInfoCreated)
    assert result.success is True
    assert ".impl/run-info.json" in result.path


def test_impl_writes_correct_content(tmp_path: Path) -> None:
    """Test that run-info.json has correct content."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    _create_impl_run_info_impl(
        tmp_path, run_id="67890", run_url="https://github.com/test/repo/actions/runs/67890"
    )

    # Read and verify content
    run_info_path = impl_dir / "run-info.json"
    content = json.loads(run_info_path.read_text(encoding="utf-8"))

    assert content["run_id"] == "67890"
    assert content["run_url"] == "https://github.com/test/repo/actions/runs/67890"


def test_impl_directory_not_found(tmp_path: Path) -> None:
    """Test error when .impl directory doesn't exist."""
    # Don't create .impl directory

    result = _create_impl_run_info_impl(
        tmp_path, run_id="12345", run_url="https://github.com/owner/repo/actions/runs/12345"
    )

    assert isinstance(result, RunInfoError)
    assert result.success is False
    assert result.error == "directory_not_found"
    assert ".impl" in result.message


def test_impl_overwrites_existing(tmp_path: Path) -> None:
    """Test that existing run-info.json is overwritten."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create existing file with different content
    run_info_path = impl_dir / "run-info.json"
    run_info_path.write_text('{"run_id": "old", "run_url": "old_url"}', encoding="utf-8")

    result = _create_impl_run_info_impl(
        tmp_path, run_id="new", run_url="https://github.com/new/url"
    )

    assert isinstance(result, RunInfoCreated)
    content = json.loads(run_info_path.read_text(encoding="utf-8"))
    assert content["run_id"] == "new"
    assert content["run_url"] == "https://github.com/new/url"


# ============================================================================
# 2. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command when .impl directory exists."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://github.com/owner/repo/actions/runs/12345"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "path" in output


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI command exits with error code when directory missing."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://github.com/owner/repo/actions/runs/12345"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "directory_not_found"


def test_cli_json_output_structure_success(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://example.com"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "path" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["path"], str)


def test_cli_json_output_structure_error(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on error."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(
        create_impl_run_info_command,
        ["--run-id", "12345", "--run-url", "https://example.com"],
        obj=ctx,
    )

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
