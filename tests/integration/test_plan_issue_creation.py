"""Integration tests for plan issue creation workflow.

Tests the full workflow from plan content to wrapped metadata block.
Uses subprocess to call the actual kit CLI command.
"""

import subprocess


def test_wrap_plan_command_produces_valid_output() -> None:
    """Test wrap-plan-in-metadata-block command returns plan as-is.

    The command returns plan content unchanged. Metadata wrapping happens
    via separate GitHub comments using render_erk_issue_event(), not in the
    initial issue body returned by this command.
    """
    plan_content = """# Test Implementation Plan

## Overview
This is a test plan for verification.

## Implementation Steps
1. First step
2. Second step
3. Third step

## Success Criteria
- All tests pass
- Code follows standards"""

    # Call the actual kit CLI command
    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input=plan_content,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # Verify plan content is returned as-is (no wrapping)
    # The command now outputs raw markdown; wrapping happens via separate comment
    assert "# Test Implementation Plan" in output
    assert "## Overview" in output
    assert "This is a test plan for verification." in output
    assert "## Implementation Steps" in output
    assert "1. First step" in output
    assert "2. Second step" in output
    assert "3. Third step" in output
    assert "## Success Criteria" in output
    assert "- All tests pass" in output
    assert "- Code follows standards" in output

    # Verify NO metadata wrapping (that now happens via separate comments)
    assert "This issue contains an implementation plan:" not in output
    assert "<details>" not in output
    assert "<summary>" not in output


def test_wrap_plan_command_handles_empty_input() -> None:
    """Test wrap-plan-in-metadata-block handles empty input gracefully."""
    # Call with empty input
    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input="",
        capture_output=True,
        text=True,
    )

    # Should fail with error
    assert result.returncode != 0
    assert "Error: Empty plan content" in result.stderr


def test_wrap_plan_command_preserves_special_characters() -> None:
    """Test wrap-plan-in-metadata-block preserves special characters."""
    plan_content = """# Plan with Special Characters

- Quotes: "double" and 'single'
- Backticks: `code snippet`
- Symbols: @#$%^&*()
- Unicode: 🔥 ✅ ❌
- Line breaks and spacing

    Indented content"""

    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input=plan_content,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # Verify all special characters are preserved
    assert '"double"' in output
    assert "'single'" in output
    assert "`code snippet`" in output
    assert "@#$%^&*()" in output
    assert "🔥" in output
    assert "✅" in output
    assert "❌" in output
    assert "Indented content" in output


def test_wrap_plan_command_with_very_long_plan() -> None:
    """Test wrap-plan-in-metadata-block handles large plans.

    The command returns plan content as-is without wrapping.
    Metadata blocks are added via separate GitHub comments.
    """
    # Create a large plan (simulate a realistic size)
    sections = []
    for i in range(20):
        sections.append(f"## Phase {i + 1}")
        for j in range(10):
            sections.append(f"- Task {i + 1}.{j + 1}: Description of task")

    plan_content = "# Large Implementation Plan\n\n" + "\n".join(sections)

    result = subprocess.run(
        ["dot-agent", "kit-command", "erk", "wrap-plan-in-metadata-block"],
        input=plan_content,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    # Verify plan content is returned as-is (no wrapping)
    assert "# Large Implementation Plan" in output

    # Verify content is complete (check first and last sections)
    assert "## Phase 1" in output
    assert "## Phase 20" in output
    assert "Task 1.1" in output
    assert "Task 20.10" in output

    # Verify NO metadata wrapping (that now happens via separate comments)
    assert "This issue contains an implementation plan:" not in output
    assert "<details>" not in output
