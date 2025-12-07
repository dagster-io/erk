"""Integration tests for get-progress kit CLI command.

Tests the complete workflow for querying progress from progress.md.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from erk_shared.impl_folder import create_impl_folder

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.get_progress import get_progress
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.mark_step import mark_step


@pytest.fixture
def impl_folder_with_steps(tmp_path: Path) -> Path:
    """Create .impl/ folder with test plan and progress."""
    plan_content = """# Test Plan

1. First step
2. Second step
3. Third step
"""
    create_impl_folder(tmp_path, plan_content, overwrite=False)
    return tmp_path


def test_get_progress_human_output(impl_folder_with_steps: Path, monkeypatch) -> None:
    """Test human-readable output format."""
    monkeypatch.chdir(impl_folder_with_steps)

    runner = CliRunner()
    result = runner.invoke(get_progress)

    assert result.exit_code == 0
    assert "Progress: 0/3 (0%)" in result.output
    assert "- [ ] 1. First step" in result.output
    assert "- [ ] 2. Second step" in result.output
    assert "- [ ] 3. Third step" in result.output


def test_get_progress_json_output(impl_folder_with_steps: Path, monkeypatch) -> None:
    """Test JSON output format."""
    monkeypatch.chdir(impl_folder_with_steps)

    runner = CliRunner()
    result = runner.invoke(get_progress, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["completed_steps"] == 0
    assert data["total_steps"] == 3
    assert data["percentage"] == 0
    assert len(data["steps"]) == 3
    assert data["steps"][0]["text"] == "1. First step"
    assert data["steps"][0]["completed"] is False


def test_get_progress_after_marking_steps(impl_folder_with_steps: Path, monkeypatch) -> None:
    """Test get-progress after marking some steps complete."""
    monkeypatch.chdir(impl_folder_with_steps)

    runner = CliRunner()

    # Mark step 1 and 2 as completed
    runner.invoke(mark_step, ["1"])
    runner.invoke(mark_step, ["2"])

    # Get progress
    result = runner.invoke(get_progress)

    assert result.exit_code == 0
    assert "Progress: 2/3 (66%)" in result.output
    assert "- [x] 1. First step" in result.output
    assert "- [x] 2. Second step" in result.output
    assert "- [ ] 3. Third step" in result.output


def test_get_progress_json_with_completed_steps(impl_folder_with_steps: Path, monkeypatch) -> None:
    """Test JSON output with some completed steps."""
    monkeypatch.chdir(impl_folder_with_steps)

    runner = CliRunner()

    # Mark step 2 as completed
    runner.invoke(mark_step, ["2"])

    # Get progress as JSON
    result = runner.invoke(get_progress, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["completed_steps"] == 1
    assert data["total_steps"] == 3
    assert data["percentage"] == 33
    assert data["steps"][0]["completed"] is False
    assert data["steps"][1]["completed"] is True
    assert data["steps"][2]["completed"] is False


def test_get_progress_missing_progress_file(tmp_path: Path, monkeypatch) -> None:
    """Test error handling when progress.md doesn't exist."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_progress)

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "No progress.md found" in result.output


def test_get_progress_all_steps_completed(impl_folder_with_steps: Path, monkeypatch) -> None:
    """Test get-progress when all steps are completed."""
    monkeypatch.chdir(impl_folder_with_steps)

    runner = CliRunner()

    # Mark all steps as completed
    runner.invoke(mark_step, ["1"])
    runner.invoke(mark_step, ["2"])
    runner.invoke(mark_step, ["3"])

    # Get progress
    result = runner.invoke(get_progress)

    assert result.exit_code == 0
    assert "Progress: 3/3 (100%)" in result.output
    assert "- [x] 1. First step" in result.output
    assert "- [x] 2. Second step" in result.output
    assert "- [x] 3. Third step" in result.output
