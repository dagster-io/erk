"""Integration tests for get-progress kit CLI command.

Tests the complete workflow for querying progress from progress.md.
Uses context injection via ErkContext.for_test() instead of monkeypatch.chdir().
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_progress import get_progress
from erk.cli.commands.exec.scripts.mark_step import mark_step
from erk_shared.context import ErkContext
from erk_shared.impl_folder import create_impl_folder


@pytest.fixture
def impl_folder_with_steps(tmp_path: Path) -> Path:
    """Create .impl/ folder with test plan and progress.

    Uses the regex-based step extraction which requires ## Step N: Title format.
    """
    plan_content = """# Test Plan

## Step 1: First step

Do the first step.

## Step 2: Second step

Do the second step.

## Step 3: Third step

Do the third step.
"""
    create_impl_folder(tmp_path, plan_content, prompt_executor=None, overwrite=False)
    return tmp_path


def test_get_progress_human_output(impl_folder_with_steps: Path) -> None:
    """Test human-readable output format."""
    runner = CliRunner()
    result = runner.invoke(
        get_progress,
        [],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 0
    assert "Progress: 0/3 (0%)" in result.output
    assert "- [ ] First step" in result.output
    assert "- [ ] Second step" in result.output
    assert "- [ ] Third step" in result.output


def test_get_progress_json_output(impl_folder_with_steps: Path) -> None:
    """Test JSON output format."""
    runner = CliRunner()
    result = runner.invoke(
        get_progress,
        ["--json"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["completed_steps"] == 0
    assert data["total_steps"] == 3
    assert data["percentage"] == 0
    assert len(data["steps"]) == 3
    assert data["steps"][0]["text"] == "First step"
    assert data["steps"][0]["completed"] is False


def test_get_progress_after_marking_steps(impl_folder_with_steps: Path) -> None:
    """Test get-progress after marking some steps complete."""
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=impl_folder_with_steps)

    # Mark step 1 and 2 as completed
    runner.invoke(mark_step, ["1"], obj=ctx)
    runner.invoke(mark_step, ["2"], obj=ctx)

    # Get progress
    result = runner.invoke(get_progress, [], obj=ctx)

    assert result.exit_code == 0
    assert "Progress: 2/3 (66%)" in result.output
    assert "- [x] First step" in result.output
    assert "- [x] Second step" in result.output
    assert "- [ ] Third step" in result.output


def test_get_progress_json_with_completed_steps(impl_folder_with_steps: Path) -> None:
    """Test JSON output with some completed steps."""
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=impl_folder_with_steps)

    # Mark step 2 as completed
    runner.invoke(mark_step, ["2"], obj=ctx)

    # Get progress as JSON
    result = runner.invoke(get_progress, ["--json"], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["completed_steps"] == 1
    assert data["total_steps"] == 3
    assert data["percentage"] == 33
    assert data["steps"][0]["completed"] is False
    assert data["steps"][1]["completed"] is True
    assert data["steps"][2]["completed"] is False


def test_get_progress_missing_progress_file(tmp_path: Path) -> None:
    """Test error handling when progress.md doesn't exist."""
    runner = CliRunner()
    result = runner.invoke(
        get_progress,
        [],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "No progress.md found" in result.output


def test_get_progress_all_steps_completed(impl_folder_with_steps: Path) -> None:
    """Test get-progress when all steps are completed."""
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=impl_folder_with_steps)

    # Mark all steps as completed
    runner.invoke(mark_step, ["1"], obj=ctx)
    runner.invoke(mark_step, ["2"], obj=ctx)
    runner.invoke(mark_step, ["3"], obj=ctx)

    # Get progress
    result = runner.invoke(get_progress, [], obj=ctx)

    assert result.exit_code == 0
    assert "Progress: 3/3 (100%)" in result.output
    assert "- [x] First step" in result.output
    assert "- [x] Second step" in result.output
    assert "- [x] Third step" in result.output
