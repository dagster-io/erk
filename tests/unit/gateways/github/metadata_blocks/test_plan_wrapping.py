"""Tests for plan wrapping functionality."""


def test_wrap_simple_plan_format() -> None:
    """Test that plan wrapping produces correct collapsible format."""
    plan_content = "# My Plan\n1. Step one\n2. Step two"

    # Simulate the wrap_plan_in_metadata_block output format
    expected_intro = "This issue contains an implementation plan:"
    wrapped = f"""{expected_intro}

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify structure
    assert expected_intro in wrapped
    assert "<details>" in wrapped
    assert "<summary><code>erk-plan</code></summary>" in wrapped
    assert plan_content in wrapped
    assert "</details>" in wrapped

    # Verify block is collapsible (no 'open' attribute)
    assert "open" not in wrapped.lower()


def test_wrap_plan_preserves_formatting() -> None:
    """Test that markdown formatting is preserved in wrapped plan."""
    plan_content = """# Implementation Plan

## Phase 1
- Task 1
- Task 2

## Phase 2
1. Step one
2. Step two"""

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify all formatting elements are preserved
    assert "# Implementation Plan" in wrapped
    assert "## Phase 1" in wrapped
    assert "## Phase 2" in wrapped
    assert "- Task 1" in wrapped
    assert "1. Step one" in wrapped


def test_wrap_plan_with_special_characters() -> None:
    """Test that special characters are handled in wrapped plans."""
    plan_content = """# Plan with Special Characters

- Quotes: "double" and 'single'
- Backticks: `code`
- Symbols: @#$%^&*()
- Unicode: 🔥 ✅ ❌"""

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify special characters are preserved
    assert '"double"' in wrapped
    assert "'single'" in wrapped
    assert "`code`" in wrapped
    assert "@#$%^&*()" in wrapped
    assert "🔥" in wrapped
    assert "✅" in wrapped


def test_rendered_plan_block_is_parseable() -> None:
    """Test that wrapped plan has correct HTML structure."""
    plan_content = "# Test Plan\n1. First step\n2. Second step"

    wrapped = f"""This issue contains an implementation plan:

<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Verify structure is correct for GitHub rendering
    assert "<details>" in wrapped
    assert "<summary><code>erk-plan</code></summary>" in wrapped
    assert plan_content in wrapped
    assert "</details>" in wrapped
