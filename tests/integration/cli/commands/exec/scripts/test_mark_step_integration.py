"""Integration tests for mark-step kit CLI command.

Tests the complete workflow for marking steps as completed/incomplete in progress.md.
Uses context injection via ErkContext.for_test() instead of monkeypatch.chdir().
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.mark_step import mark_step
from erk_shared.context import ErkContext
from erk_shared.impl_folder import create_impl_folder, parse_progress_frontmatter


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


def test_mark_step_marks_step_completed(impl_folder_with_steps: Path) -> None:
    """Test marking a step as completed updates YAML and regenerates checkboxes."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        ["2"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 0
    assert "✓ Step 2" in result.output
    assert "Progress: 1/3" in result.output

    # Verify progress.md was updated
    progress_file = impl_folder_with_steps / ".impl" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")

    # Verify YAML updated
    metadata = parse_progress_frontmatter(content)
    assert metadata is not None
    assert metadata["completed_steps"] == 1
    assert metadata["total_steps"] == 3
    assert metadata["steps"][1]["completed"] is True
    assert metadata["steps"][0]["completed"] is False
    assert metadata["steps"][2]["completed"] is False

    # Verify checkboxes regenerated
    assert "- [ ] First step" in content
    assert "- [x] Second step" in content
    assert "- [ ] Third step" in content


def test_mark_step_marks_step_incomplete(impl_folder_with_steps: Path) -> None:
    """Test marking a completed step as incomplete."""
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=impl_folder_with_steps)

    # First mark as completed
    runner.invoke(mark_step, ["2"], obj=ctx)
    # Then mark as incomplete
    result = runner.invoke(mark_step, ["2", "--incomplete"], obj=ctx)

    assert result.exit_code == 0
    assert "○ Step 2" in result.output
    assert "Progress: 0/3" in result.output

    # Verify progress.md updated
    progress_file = impl_folder_with_steps / ".impl" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")

    metadata = parse_progress_frontmatter(content)
    assert metadata is not None
    assert metadata["completed_steps"] == 0
    assert metadata["steps"][1]["completed"] is False


def test_mark_step_json_output(impl_folder_with_steps: Path) -> None:
    """Test JSON output mode."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        ["1", "--json"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["success"] is True
    assert data["step_nums"] == [1]
    assert data["completed"] is True
    assert data["total_completed"] == 1
    assert data["total_steps"] == 3


def test_mark_step_invalid_step_number(impl_folder_with_steps: Path) -> None:
    """Test error handling for invalid step number."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        ["99"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "out of range" in result.output


def test_mark_step_missing_progress_file(tmp_path: Path) -> None:
    """Test error handling when progress.md doesn't exist."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        ["1"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "No progress.md found" in result.output


def test_mark_step_multiple_steps_sequential(impl_folder_with_steps: Path) -> None:
    """Test marking multiple steps in sequence."""
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=impl_folder_with_steps)

    # Mark steps 1, 2, 3 sequentially
    result1 = runner.invoke(mark_step, ["1"], obj=ctx)
    assert result1.exit_code == 0
    assert "Progress: 1/3" in result1.output

    result2 = runner.invoke(mark_step, ["2"], obj=ctx)
    assert result2.exit_code == 0
    assert "Progress: 2/3" in result2.output

    result3 = runner.invoke(mark_step, ["3"], obj=ctx)
    assert result3.exit_code == 0
    assert "Progress: 3/3" in result3.output

    # Verify final state
    progress_file = impl_folder_with_steps / ".impl" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")

    metadata = parse_progress_frontmatter(content)
    assert metadata is not None
    assert metadata["completed_steps"] == 3
    assert all(step["completed"] for step in metadata["steps"])


def test_mark_step_multiple_steps_single_command(impl_folder_with_steps: Path) -> None:
    """Test marking multiple steps in a single command."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        ["1", "2", "3"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 0
    assert "✓ Step 1" in result.output
    assert "✓ Step 2" in result.output
    assert "✓ Step 3" in result.output
    assert "Progress: 3/3" in result.output

    # Verify progress.md was updated
    progress_file = impl_folder_with_steps / ".impl" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")

    metadata = parse_progress_frontmatter(content)
    assert metadata is not None
    assert metadata["completed_steps"] == 3
    assert all(step["completed"] for step in metadata["steps"])


def test_mark_step_multiple_steps_json_output(impl_folder_with_steps: Path) -> None:
    """Test JSON output with multiple steps."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        ["1", "3", "--json"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["success"] is True
    assert data["step_nums"] == [1, 3]
    assert data["completed"] is True
    assert data["total_completed"] == 2
    assert data["total_steps"] == 3


def test_mark_step_multiple_steps_one_invalid_fails_entire_batch(
    impl_folder_with_steps: Path,
) -> None:
    """Test that if one step is invalid, the entire batch fails with no partial writes."""
    runner = CliRunner()
    # Step 99 is invalid (out of range)
    result = runner.invoke(
        mark_step,
        ["1", "99", "2"],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "out of range" in result.output

    # Verify progress.md was NOT modified (no partial writes)
    progress_file = impl_folder_with_steps / ".impl" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")

    metadata = parse_progress_frontmatter(content)
    assert metadata is not None
    assert metadata["completed_steps"] == 0
    assert all(not step["completed"] for step in metadata["steps"])


def test_mark_step_empty_args_error(impl_folder_with_steps: Path) -> None:
    """Test error when no step numbers are provided."""
    runner = CliRunner()
    result = runner.invoke(
        mark_step,
        [],
        obj=ErkContext.for_test(cwd=impl_folder_with_steps),
    )

    assert result.exit_code == 1
    assert "Error" in result.output
    assert "At least one step number is required" in result.output
