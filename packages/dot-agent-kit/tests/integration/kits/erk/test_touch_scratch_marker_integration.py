"""Integration tests for touch-scratch-marker kit CLI command.

Tests the complete workflow for creating scratch directories and marker files.
"""

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.touch_scratch_marker import (
    touch_scratch_marker,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing.

    Returns:
        Path to the git repository root
    """
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


def test_creates_scratch_directory_without_marker(git_repo: Path, monkeypatch) -> None:
    """Test creating scratch directory without marker file."""
    monkeypatch.chdir(git_repo)

    runner = CliRunner()
    result = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-123"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert "test-session-123" in data["scratch_dir"]
    assert data["marker_path"] is None

    # Verify directory was created
    scratch_dir = git_repo / ".erk" / "scratch" / "test-session-123"
    assert scratch_dir.exists()
    assert scratch_dir.is_dir()


def test_creates_scratch_directory_with_marker(git_repo: Path, monkeypatch) -> None:
    """Test creating scratch directory with marker file."""
    monkeypatch.chdir(git_repo)

    runner = CliRunner()
    result = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-456", "--marker", "skip-plan-save"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert "test-session-456" in data["scratch_dir"]
    assert "skip-plan-save" in data["marker_path"]

    # Verify directory and marker were created
    scratch_dir = git_repo / ".erk" / "scratch" / "test-session-456"
    marker_file = scratch_dir / "skip-plan-save"
    assert scratch_dir.exists()
    assert scratch_dir.is_dir()
    assert marker_file.exists()
    assert marker_file.is_file()


def test_idempotent_directory_creation(git_repo: Path, monkeypatch) -> None:
    """Test that directory creation is idempotent (works when directory exists)."""
    monkeypatch.chdir(git_repo)

    # First call
    runner = CliRunner()
    result1 = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-789"],
    )
    assert result1.exit_code == 0

    # Second call with same session ID
    result2 = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-789"],
    )
    assert result2.exit_code == 0
    data = json.loads(result2.output)
    assert data["success"] is True


def test_errors_when_not_in_git_repo(tmp_path: Path, monkeypatch) -> None:
    """Test that command fails gracefully when not in a git repo."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-bad"],
    )

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert "error" in data


def test_errors_on_empty_session_id(git_repo: Path, monkeypatch) -> None:
    """Test error when session_id is empty."""
    monkeypatch.chdir(git_repo)

    runner = CliRunner()
    result = runner.invoke(
        touch_scratch_marker,
        ["--session-id", ""],
    )

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert "session_id cannot be empty" in data["error"]


def test_creates_multiple_markers_in_same_session(git_repo: Path, monkeypatch) -> None:
    """Test creating multiple marker files in the same session directory."""
    monkeypatch.chdir(git_repo)

    runner = CliRunner()

    # Create first marker
    result1 = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-multi", "--marker", "marker1"],
    )
    assert result1.exit_code == 0

    # Create second marker
    result2 = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-multi", "--marker", "marker2"],
    )
    assert result2.exit_code == 0

    # Verify both markers exist
    scratch_dir = git_repo / ".erk" / "scratch" / "test-session-multi"
    marker1 = scratch_dir / "marker1"
    marker2 = scratch_dir / "marker2"
    assert marker1.exists()
    assert marker2.exists()


def test_marker_with_special_characters(git_repo: Path, monkeypatch) -> None:
    """Test creating marker with special characters in filename."""
    monkeypatch.chdir(git_repo)

    runner = CliRunner()
    result = runner.invoke(
        touch_scratch_marker,
        ["--session-id", "test-session-special", "--marker", "plan-saved-to-github"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert "plan-saved-to-github" in data["marker_path"]

    # Verify marker was created
    scratch_dir = git_repo / ".erk" / "scratch" / "test-session-special"
    marker_file = scratch_dir / "plan-saved-to-github"
    assert marker_file.exists()
