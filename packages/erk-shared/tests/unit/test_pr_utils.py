"""Unit tests for plan utility functions."""

from pathlib import Path

from erk_shared.naming import generate_filename_from_title
from erk_shared.pr_utils import (
    extract_title_from_pr,
    format_error,
    resolve_plan_content,
    wrap_pr_in_metadata_block,
)
from tests.fakes.gateway.claude_installation import FakeClaudeInstallation


def test_wrap_plan_basic() -> None:
    """Test plan content is wrapped in collapsible details block with default intro.

    The function wraps the plan in a <details> block with customizable intro text,
    making GitHub issues more scannable while preserving all plan details.
    """
    plan = "## My Plan\n\n- Step 1\n- Step 2"
    result = wrap_pr_in_metadata_block(plan)

    # Should include default intro text
    assert "This issue contains an implementation plan:" in result
    # Should wrap in metadata block format
    assert "<details>" in result
    assert "</details>" in result
    assert "<summary><code>erk-plan</code></summary>" in result
    # Should include plan content
    assert plan in result


def test_wrap_plan_strips_whitespace() -> None:
    """Test plan content strips leading/trailing whitespace before wrapping."""
    plan = "\n\n  ## My Plan\n\n- Step 1\n- Step 2  \n\n"
    result = wrap_pr_in_metadata_block(plan)

    # Should strip whitespace from plan content
    assert "## My Plan\n\n- Step 1\n- Step 2" in result
    # Should include metadata block structure
    assert "<details>" in result
    assert "</details>" in result


def test_wrap_plan_custom_intro_text() -> None:
    """Test plan wrapping with custom introductory text."""
    plan = "## My Plan\n\n- Step 1"
    custom_intro = "Check out this amazing plan:"
    result = wrap_pr_in_metadata_block(plan, intro_text=custom_intro)

    # Should include custom intro text
    assert custom_intro in result
    # Should NOT include default intro text
    assert "This issue contains an implementation plan:" not in result
    # Should still wrap in details block
    assert "<details>" in result
    assert plan in result


def test_wrap_plan_complex_markdown() -> None:
    """Test plan wrapping preserves complex markdown formatting."""
    plan = """# Title

## Section

- Item 1
- Item 2

```python
def hello():
    print("world")
```

**Bold** and *italic* text."""
    result = wrap_pr_in_metadata_block(plan)

    # Should preserve all markdown content
    assert "# Title" in result
    assert "## Section" in result
    assert "```python" in result
    assert "**Bold**" in result
    # Should be wrapped
    assert "<details>" in result


def test_wrap_plan_empty() -> None:
    """Test plan wrapping with empty plan."""
    plan = ""
    result = wrap_pr_in_metadata_block(plan)

    # Should still create structure even with empty plan
    assert "<details>" in result
    assert "This issue contains an implementation plan:" in result


def test_extract_title_h1() -> None:
    """Test title extraction from H1 heading."""
    plan = "# Feature Name\n\nDetails..."
    assert extract_title_from_pr(plan) == "Feature Name"


def test_extract_title_h1_with_markdown() -> None:
    """Test title extraction removes markdown formatting."""
    plan = "# **Feature** `Name`\n\nDetails..."
    assert extract_title_from_pr(plan) == "Feature Name"


def test_extract_title_h2_fallback() -> None:
    """Test title extraction from H2 when no H1."""
    plan = "## My Feature\n\nDetails..."
    assert extract_title_from_pr(plan) == "My Feature"


def test_extract_title_first_line_fallback() -> None:
    """Test title extraction from first line when no headers."""
    plan = "Some plain text\n\nMore text..."
    assert extract_title_from_pr(plan) == "Some plain text"


def test_extract_title_skips_yaml_frontmatter() -> None:
    """Test title extraction skips YAML front matter delimiters."""
    plan = "---\ntitle: foo\n---\n# Real Title\n\nDetails..."
    assert extract_title_from_pr(plan) == "Real Title"


def test_extract_title_empty_plan() -> None:
    """Test title extraction from empty plan returns default."""
    assert extract_title_from_pr("") == "Implementation Plan"
    assert extract_title_from_pr("   \n\n  ") == "Implementation Plan"


def test_extract_title_truncates_long_titles() -> None:
    """Test title extraction truncates to 100 chars."""
    long_title = "A" * 150
    plan = f"# {long_title}\n\nDetails..."
    result = extract_title_from_pr(plan)
    assert len(result) == 100
    assert result == "A" * 100


def test_extract_title_strips_plan_prefix() -> None:
    """Test title extraction strips 'Plan: ' prefix from H1."""
    plan = "# Plan: Add Feature X\n\nDetails..."
    assert extract_title_from_pr(plan) == "Add Feature X"


def test_extract_title_strips_implementation_plan_prefix() -> None:
    """Test title extraction strips 'Implementation Plan: ' prefix from H1."""
    plan = "# Implementation Plan: Refactor Y\n\nDetails..."
    assert extract_title_from_pr(plan) == "Refactor Y"


def test_extract_title_strips_documentation_plan_prefix() -> None:
    """Test title extraction strips 'Documentation Plan: ' prefix from H1."""
    plan = "# Documentation Plan: Learn Workflow\n\nDetails..."
    assert extract_title_from_pr(plan) == "Learn Workflow"


def test_extract_title_strips_plan_prefix_h2() -> None:
    """Test title extraction strips plan prefix from H2."""
    plan = "## Plan: My Feature\n\nDetails..."
    assert extract_title_from_pr(plan) == "My Feature"


def test_extract_title_strips_plan_prefix_fallback() -> None:
    """Test title extraction strips plan prefix from first line fallback."""
    plan = "Plan: Some Feature\n\nMore text..."
    assert extract_title_from_pr(plan) == "Some Feature"


def test_extract_title_preserves_plan_in_middle() -> None:
    """Test that 'Plan' in the middle of title is preserved."""
    plan = "# The Migration Plan for Database\n\nDetails..."
    assert extract_title_from_pr(plan) == "The Migration Plan for Database"


def test_generate_filename_basic() -> None:
    """Test filename generation from simple title."""
    assert generate_filename_from_title("User Auth") == "user-auth-plan.md"


def test_generate_filename_special_chars() -> None:
    """Test filename generation removes special characters."""
    assert generate_filename_from_title("Fix: Database!!!") == "fix-database-plan.md"


def test_generate_filename_unicode() -> None:
    """Test filename generation handles unicode."""
    assert generate_filename_from_title("café Feature") == "cafe-feature-plan.md"


def test_generate_filename_emoji() -> None:
    """Test filename generation removes emojis."""
    assert generate_filename_from_title("🚀 Feature Launch 🎉") == "feature-launch-plan.md"


def test_generate_filename_collapse_hyphens() -> None:
    """Test filename generation collapses consecutive hyphens."""
    assert generate_filename_from_title("Fix:  Multiple   Spaces") == "fix-multiple-spaces-plan.md"


def test_generate_filename_empty_after_cleanup() -> None:
    """Test filename generation with only emoji returns default."""
    assert generate_filename_from_title("🚀🎉") == "plan.md"


def test_generate_filename_cjk() -> None:
    """Test filename generation removes CJK characters."""
    assert generate_filename_from_title("你好 Hello") == "hello-plan.md"


def test_generate_filename_strips_leading_trailing_hyphens() -> None:
    """Test filename generation strips edge hyphens."""
    assert generate_filename_from_title("-Feature Name-") == "feature-name-plan.md"


def test_format_error_single_action() -> None:
    """Test error formatting with single action."""
    error = format_error(
        "File not found",
        "The configuration file config.yaml does not exist",
        ["Create the configuration file"],
    )

    assert "❌ Error: File not found" in error
    assert "Details: The configuration file config.yaml does not exist" in error
    assert "Suggested action:" in error  # Singular
    assert "1. Create the configuration file" in error


def test_format_error_multiple_actions() -> None:
    """Test error formatting with multiple actions."""
    error = format_error(
        "Plan content is too minimal",
        "Plan has only 50 characters (minimum 100 required)",
        [
            "Provide a more detailed implementation plan",
            "Include specific tasks, steps, or phases",
            "Use headers and lists to structure the plan",
        ],
    )

    assert "❌ Error: Plan content is too minimal" in error
    assert "Details: Plan has only 50 characters (minimum 100 required)" in error
    assert "Suggested actions:" in error  # Plural
    assert "1. Provide a more detailed implementation plan" in error
    assert "2. Include specific tasks, steps, or phases" in error
    assert "3. Use headers and lists to structure the plan" in error


def test_format_error_empty_actions_uses_default() -> None:
    """Test error formatting with empty actions list uses default action."""
    error = format_error(
        "Unknown error",
        "Something went wrong",
        [],  # Empty actions list
    )

    assert "❌ Error: Unknown error" in error
    assert "Details: Something went wrong" in error
    assert "1. Review the error details and try again" in error


def test_format_error_blank_lines() -> None:
    """Test error formatting includes blank lines between sections."""
    error = format_error(
        "Test error",
        "Test details",
        ["Test action"],
    )

    lines = error.split("\n")

    # Find key lines
    error_line_idx = next(i for i, line in enumerate(lines) if "❌ Error:" in line)
    details_line_idx = next(i for i, line in enumerate(lines) if "Details:" in line)
    action_header_idx = next(i for i, line in enumerate(lines) if "Suggested action" in line)

    # Check blank line exists between error and details
    assert lines[error_line_idx + 1] == ""

    # Check blank line exists between details and actions
    assert lines[details_line_idx + 1] == ""

    # Check structure order
    assert error_line_idx < details_line_idx < action_header_idx


def test_format_error_action_numbering() -> None:
    """Test error formatting numbers actions sequentially."""
    error = format_error(
        "Multiple issues",
        "Several problems detected",
        ["First step", "Second step", "Third step"],
    )

    lines = error.split("\n")
    action_lines = [line for line in lines if line.strip().startswith(("1.", "2.", "3."))]

    assert len(action_lines) == 3
    assert "1. First step" in action_lines[0]
    assert "2. Second step" in action_lines[1]
    assert "3. Third step" in action_lines[2]


def test_format_error_unicode_content() -> None:
    """Test error formatting handles unicode content."""
    error = format_error(
        "配置文件错误",
        "无法读取配置文件，文件格式不正确",
        ["检查配置文件语法", "参考示例配置文件"],
    )

    assert "配置文件错误" in error
    assert "无法读取配置文件" in error
    assert "检查配置文件语法" in error
    assert "参考示例配置文件" in error


def test_format_error_long_text() -> None:
    """Test error formatting with long text."""
    long_brief = "Very long error description that exceeds normal expectations"
    long_details = "This is a very detailed error message with extensive context"
    long_action = "First suggested action with extensive detail about what to do"

    error = format_error(long_brief, long_details, [long_action])

    assert long_brief in error
    assert long_details in error
    assert long_action in error


def test_format_error_emoji_present() -> None:
    """Test error formatting includes error emoji."""
    error = format_error("Error", "Details", ["Action"])
    assert "❌" in error


# resolve_plan_content tests


def test_resolve_plan_content_plan_file_takes_priority(tmp_path: Path) -> None:
    """Verify plan_file parameter has highest priority."""
    plan_file = tmp_path / "explicit-plan.md"
    plan_file.write_text("# Explicit Plan", encoding="utf-8")

    fake_claude = FakeClaudeInstallation.for_test(
        plans={"other": "# Other Plan"},
    )

    result = resolve_plan_content(
        plan_file=plan_file,
        session_id="test-session",
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# Explicit Plan"


def test_resolve_plan_content_scratch_dir_over_claude_plans(tmp_path: Path) -> None:
    """Verify scratch directory plan takes priority over claude_installation."""
    session_id = "test-session"
    scratch_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    scratch_dir.mkdir(parents=True)
    (scratch_dir / "plan.md").write_text("# Scratch Plan", encoding="utf-8")

    fake_claude = FakeClaudeInstallation.for_test(
        plans={"other": "# Claude Plan"},
    )

    result = resolve_plan_content(
        plan_file=None,
        session_id=session_id,
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# Scratch Plan"


def test_resolve_plan_content_falls_back_to_claude_installation(tmp_path: Path) -> None:
    """Verify fallback to claude_installation when no scratch plan exists."""
    fake_claude = FakeClaudeInstallation.for_test(
        plans={"fallback": "# Claude Plan"},
    )

    result = resolve_plan_content(
        plan_file=None,
        session_id="no-scratch-session",
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# Claude Plan"


def test_resolve_plan_content_returns_none_when_no_plan(tmp_path: Path) -> None:
    """Verify None is returned when no plan found anywhere."""
    fake_claude = FakeClaudeInstallation.for_test()

    result = resolve_plan_content(
        plan_file=None,
        session_id="empty-session",
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result is None


def test_resolve_plan_content_no_session_id_uses_claude_installation(tmp_path: Path) -> None:
    """Verify scratch is skipped when session_id is None."""
    fake_claude = FakeClaudeInstallation.for_test(
        plans={"plan": "# No Session Plan"},
    )

    result = resolve_plan_content(
        plan_file=None,
        session_id=None,
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# No Session Plan"
