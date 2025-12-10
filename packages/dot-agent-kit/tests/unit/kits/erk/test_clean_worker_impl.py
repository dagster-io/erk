"""Unit tests for clean_worker_impl kit CLI command.

Tests safe removal of .worker-impl directory.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.scripts.erk.clean_worker_impl import (
    CleanSkipped,
    CleanSuccess,
    _clean_worker_impl_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.clean_worker_impl import (
    clean_worker_impl as clean_worker_impl_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    cwd: Path


# ============================================================================
# 1. Implementation Logic Tests (3 tests)
# ============================================================================


def test_impl_removes_existing_directory(tmp_path: Path) -> None:
    """Test that existing .worker-impl directory is removed."""
    worker_impl = tmp_path / ".worker-impl"
    worker_impl.mkdir()
    (worker_impl / "plan.md").write_text("test content", encoding="utf-8")

    result = _clean_worker_impl_impl(tmp_path)

    assert isinstance(result, CleanSuccess)
    assert result.success is True
    assert result.removed is True
    assert not worker_impl.exists()


def test_impl_skips_nonexistent_directory(tmp_path: Path) -> None:
    """Test that missing directory returns success with removed=False."""
    result = _clean_worker_impl_impl(tmp_path)

    assert isinstance(result, CleanSkipped)
    assert result.success is True
    assert result.removed is False
    assert "did not exist" in result.message


def test_impl_removes_nested_content(tmp_path: Path) -> None:
    """Test that nested content is removed with directory."""
    worker_impl = tmp_path / ".worker-impl"
    worker_impl.mkdir()
    subdir = worker_impl / "subdir"
    subdir.mkdir()
    (subdir / "file.txt").write_text("nested", encoding="utf-8")
    (worker_impl / "plan.md").write_text("plan", encoding="utf-8")

    result = _clean_worker_impl_impl(tmp_path)

    assert isinstance(result, CleanSuccess)
    assert result.removed is True
    assert not worker_impl.exists()


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_removes_directory(tmp_path: Path) -> None:
    """Test CLI removes existing directory."""
    runner = CliRunner()
    worker_impl = tmp_path / ".worker-impl"
    worker_impl.mkdir()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(clean_worker_impl_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["removed"] is True


def test_cli_skips_nonexistent(tmp_path: Path) -> None:
    """Test CLI succeeds when directory doesn't exist."""
    runner = CliRunner()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(clean_worker_impl_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["removed"] is False


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    worker_impl = tmp_path / ".worker-impl"
    worker_impl.mkdir()
    ctx = CLIContext(cwd=tmp_path)

    result = runner.invoke(clean_worker_impl_command, [], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "removed" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["removed"], bool)
