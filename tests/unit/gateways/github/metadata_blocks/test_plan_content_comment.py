"""Tests for format_plan_content_comment and extract_plan_from_comment."""

from erk_shared.github.metadata.plan_header import (
    extract_plan_from_comment,
    format_plan_content_comment,
)


def test_format_plan_content_comment_produces_collapsible_block() -> None:
    """Test that format_plan_content_comment uses collapsible metadata block format."""
    plan_content = "# My Plan\n1. Step one\n2. Step two"
    result = format_plan_content_comment(plan_content)

    # Verify metadata block wrapper structure
    assert "<!-- WARNING: Machine-generated" in result
    assert "<!-- erk:metadata-block:plan-body -->" in result
    assert "<!-- /erk:metadata-block:plan-body -->" in result

    # Verify collapsible details structure (open by default)
    assert "<details open>" in result
    assert "<summary><strong>📋 Implementation Plan</strong></summary>" in result
    assert "</details>" in result

    # Verify plan content is present
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_format_plan_content_comment_strips_whitespace() -> None:
    """Test that format_plan_content_comment strips leading/trailing whitespace."""
    plan_content = "\n\n  # My Plan  \n\n"
    result = format_plan_content_comment(plan_content)

    # The plan content should be stripped
    assert "# My Plan" in result
    # Verify it doesn't have excessive leading whitespace before "# My Plan"
    lines = result.split("\n")
    plan_line_idx = next(i for i, line in enumerate(lines) if "# My Plan" in line)
    assert lines[plan_line_idx].strip() == "# My Plan"


def test_extract_plan_from_comment_new_format() -> None:
    """Test extracting plan from new collapsible metadata block format."""
    comment_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# My Plan
1. Step one
2. Step two

</details>
<!-- /erk:metadata-block:plan-body -->"""

    result = extract_plan_from_comment(comment_body)

    assert result is not None
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_extract_plan_from_comment_old_format_backward_compatible() -> None:
    """Test extracting plan from old marker format (backward compatibility)."""
    comment_body = """<!-- erk:plan-content -->

# My Plan
1. Step one
2. Step two

<!-- /erk:plan-content -->"""

    result = extract_plan_from_comment(comment_body)

    assert result is not None
    assert "# My Plan" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_extract_plan_from_comment_returns_none_if_not_found() -> None:
    """Test that extract_plan_from_comment returns None if no plan markers found."""
    comment_body = "Just some regular comment text without any plan markers."

    result = extract_plan_from_comment(comment_body)

    assert result is None


def test_format_and_extract_plan_round_trip() -> None:
    """Test round-trip: format -> extract should return original plan content."""
    original_plan = """# Implementation Plan

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

    # Format the plan
    formatted = format_plan_content_comment(original_plan)

    # Extract it back
    extracted = extract_plan_from_comment(formatted)

    # Should get the original content back (stripped)
    assert extracted is not None
    assert extracted.strip() == original_plan.strip()


def test_extract_plan_prefers_new_format_over_old() -> None:
    """Test that new format is preferred when both formats are present."""
    # Unlikely scenario: both formats present. New format should win.
    comment_body = """<!-- erk:plan-content -->
Old format content
<!-- /erk:plan-content -->

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

New format content

</details>
<!-- /erk:metadata-block:plan-body -->"""

    result = extract_plan_from_comment(comment_body)

    assert result is not None
    assert "New format content" in result
    assert "Old format content" not in result
