"""Tests for format_plan_issue_body_simple function."""

from erk_shared.github.metadata.core import format_plan_issue_body_simple


def test_format_plan_issue_body_simple_basic() -> None:
    """Test format_plan_issue_body_simple produces correct collapsible format."""
    plan_content = "# My Plan\n1. Step one\n2. Step two"
    result = format_plan_issue_body_simple(plan_content)

    # Verify metadata block wrapper structure
    assert "<!-- WARNING: Machine-generated" in result
    assert "<!-- erk:metadata-block:plan-body -->" in result
    assert "<!-- /erk:metadata-block:plan-body -->" in result

    # Verify collapsible details structure
    assert "<details>" in result
    assert "<summary><strong>📋 Implementation Plan</strong></summary>" in result
    assert "</details>" in result

    # Verify plan content is present
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_format_plan_issue_body_simple_no_execution_commands() -> None:
    """Test format_plan_issue_body_simple does NOT include execution commands."""
    plan_content = "# Plan Content"
    result = format_plan_issue_body_simple(plan_content)

    # Verify no execution commands section (the key optimization)
    assert "## Execution Commands" not in result
    assert "erk plan submit" not in result
    assert "erk implement" not in result
    assert "--yolo" not in result
    assert "--dangerous" not in result


def test_format_plan_issue_body_simple_preserves_markdown() -> None:
    """Test that markdown formatting is preserved in simple body."""
    plan_content = """# Implementation Plan

## Phase 1
- Task 1
- Task 2

## Phase 2
1. Step one
2. Step two

```python
def example():
    pass
```"""

    result = format_plan_issue_body_simple(plan_content)

    # Verify all formatting elements are preserved
    assert "# Implementation Plan" in result
    assert "## Phase 1" in result
    assert "## Phase 2" in result
    assert "- Task 1" in result
    assert "1. Step one" in result
    assert "```python" in result
    assert "def example():" in result
