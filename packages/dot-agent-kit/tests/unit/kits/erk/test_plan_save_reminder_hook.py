"""Unit tests for plan-save-reminder-hook command."""

import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_reminder_hook import (
    plan_save_reminder_hook,
)


def test_no_plans_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test when ~/.claude/plans/ doesn't exist."""
    runner = CliRunner()

    # Mock Path.home() to return tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert result.output == ""


def test_empty_plans_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test when ~/.claude/plans/ is empty."""
    runner = CliRunner()
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert result.output == ""


def test_recent_plan_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test when a recent plan file exists."""
    runner = CliRunner()
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a plan file (will have current mtime)
    plan_file = plans_dir / "test-plan.md"
    plan_file.write_text("# Test Plan\n\n- Step 1", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert "Recent plan detected" in result.output
    assert "/erk:save-plan" in result.output


def test_old_plan_not_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test when plan file is older than 5 minutes."""
    runner = CliRunner()
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a plan file
    plan_file = plans_dir / "old-plan.md"
    plan_file.write_text("# Old Plan\n\n- Step 1", encoding="utf-8")

    # Set mtime to 6 minutes ago
    old_time = time.time() - (6 * 60)
    import os

    os.utime(plan_file, (old_time, old_time))

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert result.output == ""


def test_non_md_files_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that non-.md files are ignored."""
    runner = CliRunner()
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a non-md file
    other_file = plans_dir / "notes.txt"
    other_file.write_text("Some notes", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert result.output == ""


def test_multiple_plans_any_recent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that reminder shows if any plan is recent."""
    runner = CliRunner()
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    import os

    # Create an old plan
    old_plan = plans_dir / "old-plan.md"
    old_plan.write_text("# Old Plan", encoding="utf-8")
    old_time = time.time() - (10 * 60)
    os.utime(old_plan, (old_time, old_time))

    # Create a recent plan
    new_plan = plans_dir / "new-plan.md"
    new_plan.write_text("# New Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert "Recent plan detected" in result.output


def test_directories_in_plans_folder_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that directories inside plans folder are ignored."""
    runner = CliRunner()
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a subdirectory (should be ignored)
    subdir = plans_dir / "subdir.md"  # Named to look like .md but is a directory
    subdir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(plan_save_reminder_hook)

    assert result.exit_code == 0
    assert result.output == ""
