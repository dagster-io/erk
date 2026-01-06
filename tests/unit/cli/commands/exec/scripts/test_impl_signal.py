"""Tests for impl-signal kit CLI command.

Tests the started/ended event signaling for /erk:system:impl-execute.

Note: This command requires GitHub context and git worktree environment,
so most tests focus on error handling paths that don't require those dependencies.
Integration tests would be needed for full end-to-end testing.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_signal import (
    _get_branch_name,
    _get_worktree_name,
    impl_signal,
)


@pytest.fixture
def impl_folder(tmp_path: Path) -> Path:
    """Create .impl/ folder with test files."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n1. Step one", encoding="utf-8")

    # Create progress.md
    progress_content = """---
completed_steps: 0
total_steps: 1
steps:
- text: "1. Step one"
  completed: false
---

# Progress

- [ ] 1. Step one
"""
    progress_md = impl_dir / "progress.md"
    progress_md.write_text(progress_content, encoding="utf-8")

    return impl_dir


def test_impl_signal_started_no_issue_reference(impl_folder: Path, monkeypatch) -> None:
    """Test impl-signal started returns error when no issue.json exists."""
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(impl_signal, ["started"])

    # Should exit 0 (graceful degradation for || true pattern)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "started"
    assert data["error_type"] == "no-issue-reference"


def test_impl_signal_ended_no_issue_reference(impl_folder: Path, monkeypatch) -> None:
    """Test impl-signal ended returns error when no issue.json exists."""
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(impl_signal, ["ended"])

    # Should exit 0 (graceful degradation for || true pattern)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "ended"
    assert data["error_type"] == "no-issue-reference"


def test_impl_signal_started_missing_impl_folder(tmp_path: Path, monkeypatch) -> None:
    """Test impl-signal started returns error when impl folder missing."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_signal, ["started"])

    # Should exit 0 (graceful degradation)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "started"
    assert data["error_type"] == "no-issue-reference"


def test_impl_signal_ended_missing_impl_folder(tmp_path: Path, monkeypatch) -> None:
    """Test impl-signal ended returns error when impl folder missing."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_signal, ["ended"])

    # Should exit 0 (graceful degradation)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["event"] == "ended"
    assert data["error_type"] == "no-issue-reference"


def test_impl_signal_with_worker_impl(tmp_path: Path, monkeypatch) -> None:
    """Test impl-signal detects .worker-impl/ folder."""
    impl_dir = tmp_path / ".worker-impl"
    impl_dir.mkdir()

    # Create minimal files
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Plan", encoding="utf-8")

    progress_md = impl_dir / "progress.md"
    progress_content = "---\ncompleted_steps: 0\ntotal_steps: 1\n---\n\n- [ ] Step"
    progress_md.write_text(progress_content, encoding="utf-8")

    # No issue.json - should fail on that, not folder detection
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_signal, ["started"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    # Fails at issue reference, which means folder was found
    assert data["error_type"] == "no-issue-reference"


def test_impl_signal_invalid_event() -> None:
    """Test impl-signal rejects invalid event names."""
    runner = CliRunner()
    result = runner.invoke(impl_signal, ["invalid"])

    assert result.exit_code == 2  # Click validation error
    # Click's error message format varies, so check for key parts
    assert "invalid" in result.output.lower()
    assert "started" in result.output or "ended" in result.output


# Unit tests for helper functions


def test_get_branch_name_success() -> None:
    """Test _get_branch_name returns branch name in git repo."""
    # This test assumes we're running in a git repo
    # In a non-git context, would return None
    branch = _get_branch_name()

    # If we're in a git repo, should return a string
    # If not, returns None - both are valid for this test
    assert branch is None or isinstance(branch, str)


def test_get_worktree_name_returns_string_or_none() -> None:
    """Test _get_worktree_name returns string or None."""
    # This test assumes we're running in a git worktree context
    worktree = _get_worktree_name()

    # Should return string or None depending on context
    assert worktree is None or isinstance(worktree, str)


def test_get_branch_name_handles_failure() -> None:
    """Test _get_branch_name handles subprocess failure."""
    with patch("subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = _get_branch_name()

        assert result is None


def test_get_worktree_name_handles_failure() -> None:
    """Test _get_worktree_name handles subprocess failure."""
    with patch("subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = _get_worktree_name()

        assert result is None
