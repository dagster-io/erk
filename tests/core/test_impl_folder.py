"""Tests for implementation folder management utilities."""

import json
from pathlib import Path

import pytest

from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.metadata_blocks import (
    find_metadata_block,
    parse_metadata_blocks,
)
from erk_shared.impl_folder import (
    add_worktree_creation_comment,
    create_impl_folder,
    extract_steps_from_frontmatter,
    extract_steps_from_plan,
    extract_steps_from_plan_regex,
    extract_steps_from_plan_with_fallback,
    get_impl_path,
    get_progress_path,
    has_issue_reference,
    parse_progress_frontmatter,
    read_issue_reference,
    read_last_dispatched_run_id,
    read_plan_author,
    save_issue_reference,
    validate_issue_linkage,
    validate_progress_schema,
)
from erk_shared.prompt_executor.fake import FakePromptExecutor


def _make_executor(steps: list[str]) -> FakePromptExecutor:
    """Create a FakePromptExecutor that returns the given steps as JSON."""
    return FakePromptExecutor(output=json.dumps(steps))


# =============================================================================
# Regex-Based Step Extraction Tests (New Primary Extraction Method)
# =============================================================================


def test_extract_steps_from_plan_regex_basic() -> None:
    """Test basic step extraction with ## Step N: Title format."""
    plan_content = """# Implementation Plan

## Step 1: Create database schema
Details here...

## Step 2: Add API endpoints
More details...

## Step 3: Write tests
Final details...
"""
    steps = extract_steps_from_plan_regex(plan_content)
    assert steps == ["Create database schema", "Add API endpoints", "Write tests"]


def test_extract_steps_from_plan_regex_without_colon() -> None:
    """Test step extraction with ## Step N Title (no colon) format."""
    plan_content = """# Plan

## Step 1 First step title
## Step 2 Second step title
"""
    steps = extract_steps_from_plan_regex(plan_content)
    assert steps == ["First step title", "Second step title"]


def test_extract_steps_from_plan_regex_empty() -> None:
    """Test regex extraction returns empty list when no steps found."""
    plan_content = """# Plan

This plan has no steps in the expected format.

1. Regular numbered list
2. Another item
"""
    steps = extract_steps_from_plan_regex(plan_content)
    assert steps == []


def test_extract_steps_from_plan_regex_mixed_headers() -> None:
    """Test that only ## Step N headers are extracted, not other headers."""
    plan_content = """# Main Title

## Overview
Some overview text.

## Step 1: Actual step one
Implementation details.

## Context
More context.

## Step 2: Actual step two
More implementation.

### Step 3: Wrong level heading (should not match)
This should not be extracted.
"""
    steps = extract_steps_from_plan_regex(plan_content)
    # Only ## Step N headers should match, not ### or ## without Step
    assert steps == ["Actual step one", "Actual step two"]


def test_extract_steps_from_plan_regex_non_sequential() -> None:
    """Test that non-sequential step numbers are still extracted."""
    plan_content = """## Step 1: First
## Step 5: Fifth
## Step 10: Tenth
"""
    steps = extract_steps_from_plan_regex(plan_content)
    assert steps == ["First", "Fifth", "Tenth"]


# =============================================================================
# Frontmatter-Based Step Extraction Tests
# =============================================================================


def test_extract_steps_from_frontmatter_basic() -> None:
    """Test basic step extraction from YAML frontmatter."""
    plan_content = """---
steps:
  - name: "First step"
  - name: "Second step"
  - name: "Third step"
---

# Implementation Plan

Content here...
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps == ["First step", "Second step", "Third step"]


def test_extract_steps_from_frontmatter_no_frontmatter() -> None:
    """Test returns None when no frontmatter present."""
    plan_content = """# Plan

No frontmatter here.
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps is None


def test_extract_steps_from_frontmatter_no_steps_key() -> None:
    """Test returns None when frontmatter exists but no steps key."""
    plan_content = """---
title: "My Plan"
author: "Test"
---

# Plan
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps is None


def test_extract_steps_from_frontmatter_steps_not_list() -> None:
    """Test returns None when steps is not a list."""
    plan_content = """---
steps: "not a list"
---

# Plan
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps is None


def test_extract_steps_from_frontmatter_empty_steps() -> None:
    """Test returns empty list when steps array is empty."""
    plan_content = """---
steps: []
---

# Plan
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps == []


def test_extract_steps_from_frontmatter_invalid_yaml() -> None:
    """Test returns None for invalid YAML."""
    plan_content = """---
steps: [invalid yaml
---

# Plan
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps is None


def test_extract_steps_from_frontmatter_converts_to_strings() -> None:
    """Test that non-string name values are converted to strings."""
    plan_content = """---
steps:
  - name: 123
  - name: true
  - name: "Normal string"
---

# Plan
"""
    steps = extract_steps_from_frontmatter(plan_content)
    assert steps == ["123", "True", "Normal string"]


def test_extract_steps_from_frontmatter_skips_invalid_entries() -> None:
    """Test that entries without 'name' key are skipped."""
    plan_content = """---
steps:
  - name: "Valid step"
  - invalid: "No name key"
  - "Plain string without dict"
  - name: "Another valid"
---

# Plan
"""
    steps = extract_steps_from_frontmatter(plan_content)
    # Only dict entries with 'name' key are extracted
    assert steps == ["Valid step", "Another valid"]


# =============================================================================
# Frontmatter-First Extraction with Fallback Tests
# =============================================================================


def test_extract_steps_with_fallback_uses_frontmatter_when_present() -> None:
    """Test frontmatter is used when present."""
    plan_content = """---
steps:
  - name: "From frontmatter"
---

## Step 1: From regex

Should ignore regex when frontmatter exists.
"""
    steps = extract_steps_from_plan_with_fallback(plan_content)
    assert steps == ["From frontmatter"]


def test_extract_steps_with_fallback_uses_regex_without_frontmatter() -> None:
    """Test regex fallback when no frontmatter steps."""
    plan_content = """# Plan

## Step 1: First from regex
## Step 2: Second from regex
"""
    steps = extract_steps_from_plan_with_fallback(plan_content)
    assert steps == ["First from regex", "Second from regex"]


def test_extract_steps_with_fallback_uses_regex_when_no_steps_key() -> None:
    """Test regex fallback when frontmatter exists but no steps key."""
    plan_content = """---
title: "My Plan"
---

## Step 1: From regex
"""
    steps = extract_steps_from_plan_with_fallback(plan_content)
    assert steps == ["From regex"]


def test_extract_steps_with_fallback_returns_empty_for_empty_frontmatter_steps() -> None:
    """Test empty frontmatter steps returns empty (doesn't fallback)."""
    plan_content = """---
steps: []
---

## Step 1: From regex

This regex match should be ignored because frontmatter steps exists (even if empty).
"""
    steps = extract_steps_from_plan_with_fallback(plan_content)
    # Empty list from frontmatter is authoritative, doesn't fallback to regex
    assert steps == []


# =============================================================================
# create_impl_folder with Frontmatter Tests
# =============================================================================


def test_create_impl_folder_with_frontmatter_steps(tmp_path: Path) -> None:
    """Test create_impl_folder uses frontmatter steps."""
    plan_content = """---
steps:
  - name: "Frontmatter step one"
  - name: "Frontmatter step two"
---

# Plan

## Step 1: Regex step should be ignored

Content...
"""
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Should use frontmatter steps, not regex
    assert "- [ ] Frontmatter step one" in progress_content
    assert "- [ ] Frontmatter step two" in progress_content
    assert "Regex step" not in progress_content
    assert "total_steps: 2" in progress_content


def test_create_impl_folder_warns_on_no_steps(tmp_path: Path, capsys) -> None:
    """Test create_impl_folder warns when no steps found."""
    plan_content = """# Plan with no extractable steps

No frontmatter, and no ## Step N: headers.
"""
    create_impl_folder(tmp_path, plan_content, None, overwrite=False)

    captured = capsys.readouterr()
    assert "No steps found in plan. Step tracking disabled." in captured.err


def test_create_impl_folder_basic(tmp_path: Path) -> None:
    """Test creating a plan folder with basic plan content.

    Uses new ## Step N: format for regex-based extraction.
    """
    plan_content = """# Implementation Plan: Test Feature

## Objective
Build a test feature.

## Step 1: Create module
Details about creating the module.

## Step 2: Add tests
Details about adding tests.

## Step 3: Update documentation
Details about updating docs.
"""
    # No executor needed - extraction is now regex-based
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)

    # Verify folder structure
    assert plan_folder.exists()
    assert plan_folder == tmp_path / ".impl"

    # Verify plan.md exists and has correct content
    plan_file = plan_folder / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content

    # Verify progress.md exists with step titles as checkboxes
    progress_file = plan_folder / "progress.md"
    assert progress_file.exists()
    progress_content = progress_file.read_text(encoding="utf-8")
    assert "- [ ] Create module" in progress_content
    assert "- [ ] Add tests" in progress_content
    assert "- [ ] Update documentation" in progress_content


def test_create_impl_folder_already_exists(tmp_path: Path) -> None:
    """Test that creating a plan folder when one exists raises error."""
    plan_content = "# Test Plan\n\n## Step 1: Step one\n"

    # Create first time - should succeed
    create_impl_folder(tmp_path, plan_content, None, overwrite=False)

    # Try to create again - should raise
    with pytest.raises(FileExistsError, match="Implementation folder already exists"):
        create_impl_folder(tmp_path, plan_content, None, overwrite=False)


def test_create_impl_folder_overwrite_replaces_existing(tmp_path: Path) -> None:
    """Test that overwrite=True removes existing .impl/ folder before creating new one.

    This is the fix for GitHub issue #2595 where creating a worktree from a branch
    with an existing .impl/ folder would fail because the folder was inherited.
    """
    old_plan = "# Old Plan\n\n## Step 1: Old step one\n## Step 2: Old step two\n"
    new_plan = (
        "# New Plan\n\n## Step 1: New step one\n"
        "## Step 2: New step two\n## Step 3: New step three\n"
    )

    # Create first .impl/ folder
    impl_folder = create_impl_folder(tmp_path, old_plan, None, overwrite=False)
    old_plan_file = impl_folder / "plan.md"
    old_progress_file = impl_folder / "progress.md"

    # Verify old content
    assert old_plan_file.read_text(encoding="utf-8") == old_plan
    old_progress_content = old_progress_file.read_text(encoding="utf-8")
    assert "Old step one" in old_progress_content
    assert "total_steps: 2" in old_progress_content

    # Create again with overwrite=True - should succeed and replace content
    new_impl_folder = create_impl_folder(tmp_path, new_plan, None, overwrite=True)

    # Verify new content replaced old
    assert new_impl_folder == impl_folder  # Same path
    new_plan_file = new_impl_folder / "plan.md"
    new_progress_file = new_impl_folder / "progress.md"

    assert new_plan_file.read_text(encoding="utf-8") == new_plan
    new_progress_content = new_progress_file.read_text(encoding="utf-8")
    assert "New step one" in new_progress_content
    assert "New step two" in new_progress_content
    assert "New step three" in new_progress_content
    assert "total_steps: 3" in new_progress_content

    # Verify old content is gone
    assert "Old" not in new_plan_file.read_text(encoding="utf-8")
    assert "Old" not in new_progress_content


def test_create_impl_folder_with_multiple_steps(tmp_path: Path) -> None:
    """Test creating plan folder with multiple steps using ## Step N: format."""
    plan_content = """# Complex Plan

## Overview
Complex implementation plan.

## Step 1: Main step one
Description of step one.

## Step 2: Main step two
Description of step two.

## Step 3: Main step three
Description of step three.
"""
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify all steps are in progress.md
    assert "- [ ] Main step one" in progress_content
    assert "- [ ] Main step two" in progress_content
    assert "- [ ] Main step three" in progress_content
    assert "total_steps: 3" in progress_content


def test_create_impl_folder_empty_plan(tmp_path: Path) -> None:
    """Test creating plan folder with empty or no-steps plan.

    This is the fix for GitHub issue #3274: Empty plans must still generate
    valid YAML frontmatter with steps: [], total_steps: 0, completed_steps: 0.
    Previously, empty plans returned plain markdown without frontmatter,
    causing step extraction to fail with "Progress file missing 'steps' array".
    """
    plan_content = """# Empty Plan

This plan has no steps in ## Step N: format.
Just some text with numbered lists:

1. First item
2. Second item
"""
    # No steps match the ## Step N: regex pattern
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Should create progress.md with message about no steps
    assert progress_file.exists()
    assert "No steps detected" in progress_content

    # Critical: Must still have valid YAML frontmatter
    assert progress_content.startswith("---\n")
    metadata = parse_progress_frontmatter(progress_content)
    assert metadata is not None
    assert metadata["steps"] == []
    assert metadata["total_steps"] == 0
    assert metadata["completed_steps"] == 0

    # Schema validation should pass
    errors = validate_progress_schema(progress_file)
    assert errors == []


def test_get_impl_path_exists(tmp_path: Path) -> None:
    """Test getting plan path when it exists."""
    plan_content = "# Test\n\n## Step 1: Step one\n"
    create_impl_folder(tmp_path, plan_content, None, overwrite=False)

    plan_path = get_impl_path(tmp_path)
    assert plan_path is not None
    assert plan_path == tmp_path / ".impl" / "plan.md"
    assert plan_path.exists()


def test_get_impl_path_not_exists(tmp_path: Path) -> None:
    """Test getting plan path when it doesn't exist."""
    plan_path = get_impl_path(tmp_path)
    assert plan_path is None


def test_get_progress_path_exists(tmp_path: Path) -> None:
    """Test getting progress path when it exists."""
    plan_content = "# Test\n\n## Step 1: Step one\n"
    create_impl_folder(tmp_path, plan_content, None, overwrite=False)

    progress_path = get_progress_path(tmp_path)
    assert progress_path is not None
    assert progress_path == tmp_path / ".impl" / "progress.md"
    assert progress_path.exists()


def test_get_progress_path_not_exists(tmp_path: Path) -> None:
    """Test getting progress path when it doesn't exist."""
    progress_path = get_progress_path(tmp_path)
    assert progress_path is None


def test_extract_steps_llm_returns_json(tmp_path: Path) -> None:
    """Test LLM-based step extraction with FakePromptExecutor."""
    plan = """# Plan

1. First step
2. Second step
3. Third step
"""
    # Configure executor to return specific steps
    executor = _make_executor(["1. First step", "2. Second step", "3. Third step"])
    steps = extract_steps_from_plan(plan, executor)
    assert len(steps) == 3
    assert "1. First step" in steps
    assert "2. Second step" in steps
    assert "3. Third step" in steps


def test_extract_steps_llm_empty_response(tmp_path: Path) -> None:
    """Test LLM returning empty array."""
    plan = """# Plan

Just text, no steps.
"""
    executor = _make_executor([])
    steps = extract_steps_from_plan(plan, executor)
    assert len(steps) == 0


def test_extract_steps_llm_handles_markdown_code_block(tmp_path: Path) -> None:
    """Test that LLM response wrapped in markdown code block is handled."""
    plan = "# Plan\n\n1. Step"
    # Simulate LLM wrapping response in code block
    executor = FakePromptExecutor(output='```json\n["1. Step"]\n```')
    steps = extract_steps_from_plan(plan, executor)
    assert steps == ["1. Step"]


def test_extract_steps_llm_failure_raises_runtime_error() -> None:
    """Test that LLM execution failure raises RuntimeError."""
    plan = "# Plan\n\n1. Step"
    executor = FakePromptExecutor(should_fail=True, error="API error")
    with pytest.raises(RuntimeError, match="LLM step extraction failed"):
        extract_steps_from_plan(plan, executor)


def test_extract_steps_llm_invalid_json_warns_and_returns_empty(capsys) -> None:
    """Test that invalid JSON response warns loudly and returns empty list."""
    plan = "# Plan\n\n1. Step"
    executor = FakePromptExecutor(output="not valid json")

    result = extract_steps_from_plan(plan, executor)

    # Should return empty list instead of raising
    assert result == []

    # Verify diagnostic output was written to stderr
    captured = capsys.readouterr()
    assert "WARNING: LLM returned invalid JSON for step extraction" in captured.err
    assert "Falling back to empty steps list" in captured.err


def test_extract_steps_llm_non_list_raises_runtime_error() -> None:
    """Test that non-list JSON response raises RuntimeError."""
    plan = "# Plan\n\n1. Step"
    executor = FakePromptExecutor(output='{"step": "1. Step"}')
    with pytest.raises(RuntimeError, match="LLM returned non-list"):
        extract_steps_from_plan(plan, executor)


def test_extract_steps_llm_non_string_item_raises_runtime_error() -> None:
    """Test that non-string items in list raise RuntimeError."""
    plan = "# Plan\n\n1. Step"
    executor = FakePromptExecutor(output='["1. Step", 123]')
    with pytest.raises(RuntimeError, match="Step 1 is not a string"):
        extract_steps_from_plan(plan, executor)


def test_extract_steps_llm_empty_output_warns_and_returns_empty(capsys) -> None:
    """Test that empty LLM output warns loudly and returns empty list.

    This tests the case where Claude CLI returns exit code 0 (success=True)
    but produces empty stdout. This gracefully degrades to an empty steps list,
    consistent with how invalid JSON is handled.
    """
    plan = "# Plan\n\n1. Step one\n2. Step two"
    # FakePromptExecutor with empty output simulates LLM returning empty stdout
    executor = FakePromptExecutor(output="")

    result = extract_steps_from_plan(plan, executor)

    # Should return empty list instead of raising
    assert result == []

    # Verify diagnostic output was written to stderr
    captured = capsys.readouterr()
    assert "WARNING: LLM returned empty output" in captured.err
    assert "Model: sonnet" in captured.err
    assert "Prompt length:" in captured.err
    assert "First 500 chars of prompt:" in captured.err
    assert "Falling back to empty steps list" in captured.err


def test_create_impl_folder_generates_frontmatter(tmp_path: Path) -> None:
    """Test that creating a plan folder generates YAML front matter in progress.md."""
    plan_content = """# Test Plan

## Step 1: First step
Details.

## Step 2: Second step
Details.

## Step 3: Third step
Details.
"""
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify front matter exists
    assert progress_content.startswith("---\n")
    assert "completed_steps: 0" in progress_content
    assert "total_steps: 3" in progress_content
    assert "---\n\n" in progress_content


def test_create_impl_folder_generates_steps_array(tmp_path: Path) -> None:
    """Test that creating a plan folder generates steps array in YAML frontmatter."""
    plan_content = """# Test Plan

## Step 1: First step
Details.

## Step 2: Second step
Details.

## Step 3: Third step
Details.
"""
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Parse frontmatter to verify steps array
    metadata = parse_progress_frontmatter(progress_content)
    assert metadata is not None
    assert "steps" in metadata
    assert isinstance(metadata["steps"], list)
    assert len(metadata["steps"]) == 3

    # Verify each step has number, title, and completed fields
    for i, step in enumerate(metadata["steps"]):
        assert "number" in step
        assert "title" in step
        assert "completed" in step
        assert step["number"] == i + 1
        assert isinstance(step["completed"], bool)
        assert step["completed"] is False  # All start uncompleted

    # Verify step titles
    assert metadata["steps"][0]["title"] == "First step"
    assert metadata["steps"][1]["title"] == "Second step"
    assert metadata["steps"][2]["title"] == "Third step"

    # Verify current_step starts at 0
    assert metadata["current_step"] == 0


def test_parse_progress_frontmatter_valid(tmp_path: Path) -> None:
    """Test parsing valid YAML front matter."""
    content = """---
completed_steps: 3
total_steps: 10
---

# Progress Tracking

- [x] 1. Step one
- [x] 2. Step two
- [x] 3. Step three
- [ ] 4. Step four
"""
    result = parse_progress_frontmatter(content)

    assert result is not None
    assert result["completed_steps"] == 3
    assert result["total_steps"] == 10


def test_parse_progress_frontmatter_missing(tmp_path: Path) -> None:
    """Test parsing progress file without front matter."""
    content = """# Progress Tracking

- [ ] 1. Step one
- [ ] 2. Step two
"""
    result = parse_progress_frontmatter(content)

    assert result is None


def test_parse_progress_frontmatter_invalid_yaml(tmp_path: Path) -> None:
    """Test parsing progress file with invalid YAML."""
    content = """---
completed_steps: [invalid yaml
total_steps: 10
---

# Progress Tracking
"""
    result = parse_progress_frontmatter(content)

    assert result is None


def test_parse_progress_frontmatter_missing_fields(tmp_path: Path) -> None:
    """Test parsing front matter with missing required fields."""
    content = """---
completed_steps: 3
---

# Progress Tracking
"""
    result = parse_progress_frontmatter(content)

    assert result is None


# ============================================================================
# Issue Reference Storage Tests
# ============================================================================


def test_save_issue_reference_success(tmp_path: Path) -> None:
    """Test saving issue reference to .plan/issue.json."""
    # Create .plan/ directory
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Save issue reference
    save_issue_reference(
        plan_dir, issue_number=42, issue_url="https://github.com/owner/repo/issues/42"
    )

    # Verify file created
    issue_file = plan_dir / "issue.json"
    assert issue_file.exists()

    # Verify content
    content = issue_file.read_text(encoding="utf-8")
    import json

    data = json.loads(content)
    assert data["issue_number"] == 42
    assert data["issue_url"] == "https://github.com/owner/repo/issues/42"
    assert "created_at" in data
    assert "synced_at" in data


def test_save_issue_reference_plan_dir_not_exists(tmp_path: Path) -> None:
    """Test save_issue_reference raises error when plan dir doesn't exist."""
    impl_dir = tmp_path / ".impl"
    # Don't create the directory

    with pytest.raises(FileNotFoundError, match="Implementation directory does not exist"):
        save_issue_reference(impl_dir, 42, "http://url")


def test_save_issue_reference_overwrites_existing(tmp_path: Path) -> None:
    """Test save_issue_reference overwrites existing issue.json."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Save first reference
    save_issue_reference(plan_dir, 10, "http://url/10")

    # Overwrite with new reference
    save_issue_reference(plan_dir, 20, "http://url/20")

    # Verify latest reference saved
    ref = read_issue_reference(plan_dir)
    assert ref is not None
    assert ref.issue_number == 20
    assert ref.issue_url == "http://url/20"


def test_save_issue_reference_timestamps(tmp_path: Path) -> None:
    """Test save_issue_reference generates ISO 8601 timestamps."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    save_issue_reference(plan_dir, 1, "http://url")

    issue_file = plan_dir / "issue.json"
    import json

    data = json.loads(issue_file.read_text(encoding="utf-8"))

    # Verify timestamps are ISO 8601 format
    assert "T" in data["created_at"]
    assert ":" in data["created_at"]
    assert "T" in data["synced_at"]
    assert ":" in data["synced_at"]


def test_read_issue_reference_success(tmp_path: Path) -> None:
    """Test reading existing issue reference."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Save reference
    save_issue_reference(plan_dir, 42, "https://github.com/owner/repo/issues/42")

    # Read it back
    ref = read_issue_reference(plan_dir)

    assert ref is not None
    assert ref.issue_number == 42
    assert ref.issue_url == "https://github.com/owner/repo/issues/42"
    assert ref.created_at is not None
    assert ref.synced_at is not None


def test_read_issue_reference_not_exists(tmp_path: Path) -> None:
    """Test read_issue_reference returns None when file doesn't exist."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    ref = read_issue_reference(plan_dir)

    assert ref is None


def test_read_issue_reference_invalid_json(tmp_path: Path) -> None:
    """Test read_issue_reference returns None for invalid JSON."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Create invalid JSON file
    issue_file = plan_dir / "issue.json"
    issue_file.write_text("not valid json", encoding="utf-8")

    ref = read_issue_reference(plan_dir)

    assert ref is None


def test_read_issue_reference_missing_fields(tmp_path: Path) -> None:
    """Test read_issue_reference returns None when required fields missing."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Create JSON with missing fields
    issue_file = plan_dir / "issue.json"
    import json

    data = {"issue_number": 42}  # Missing other required fields
    issue_file.write_text(json.dumps(data), encoding="utf-8")

    ref = read_issue_reference(plan_dir)

    assert ref is None


def test_read_issue_reference_all_fields_present(tmp_path: Path) -> None:
    """Test read_issue_reference returns IssueReference with all fields."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Create complete JSON
    issue_file = plan_dir / "issue.json"
    import json

    data = {
        "issue_number": 123,
        "issue_url": "https://github.com/owner/repo/issues/123",
        "created_at": "2025-01-01T10:00:00Z",
        "synced_at": "2025-01-01T11:00:00Z",
    }
    issue_file.write_text(json.dumps(data), encoding="utf-8")

    ref = read_issue_reference(plan_dir)

    assert ref is not None
    assert ref.issue_number == 123
    assert ref.issue_url == "https://github.com/owner/repo/issues/123"
    assert ref.created_at == "2025-01-01T10:00:00Z"
    assert ref.synced_at == "2025-01-01T11:00:00Z"


def test_has_issue_reference_exists(tmp_path: Path) -> None:
    """Test has_issue_reference returns True when file exists."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    save_issue_reference(plan_dir, 42, "http://url")

    assert has_issue_reference(plan_dir) is True


def test_has_issue_reference_not_exists(tmp_path: Path) -> None:
    """Test has_issue_reference returns False when file doesn't exist."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    assert has_issue_reference(plan_dir) is False


def test_has_issue_reference_plan_dir_not_exists(tmp_path: Path) -> None:
    """Test has_issue_reference returns False when plan dir doesn't exist."""
    plan_dir = tmp_path / ".impl"
    # Don't create directory

    assert has_issue_reference(plan_dir) is False


def test_issue_reference_roundtrip(tmp_path: Path) -> None:
    """Test complete workflow: save -> read -> verify."""
    plan_dir = tmp_path / ".impl"
    plan_dir.mkdir()

    # Save reference
    issue_num = 999
    issue_url = "https://github.com/test/repo/issues/999"
    save_issue_reference(plan_dir, issue_num, issue_url)

    # Verify has_issue_reference detects it
    assert has_issue_reference(plan_dir) is True

    # Read reference back
    ref = read_issue_reference(plan_dir)

    # Verify all fields match
    assert ref is not None
    assert ref.issue_number == issue_num
    assert ref.issue_url == issue_url
    # Timestamps should exist (not testing exact values since they're generated)
    assert len(ref.created_at) > 0
    assert len(ref.synced_at) > 0


def test_issue_reference_with_plan_folder(tmp_path: Path) -> None:
    """Test issue reference integration with plan folder creation."""
    # Create plan folder
    plan_content = "# Test Plan\n\n## Step 1: Step one\n"
    plan_folder = create_impl_folder(tmp_path, plan_content, None, overwrite=False)

    # Initially no issue reference
    assert has_issue_reference(plan_folder) is False

    # Save issue reference
    save_issue_reference(plan_folder, 42, "http://url/42")

    # Verify reference exists
    assert has_issue_reference(plan_folder) is True

    # Read and verify
    ref = read_issue_reference(plan_folder)
    assert ref is not None
    assert ref.issue_number == 42


# ============================================================================
# Worktree Creation Comment Tests
# ============================================================================


def test_add_worktree_creation_comment_success(tmp_path: Path) -> None:
    """Test posting GitHub comment documenting worktree creation."""
    # Create fake GitHub issues with an existing issue
    from datetime import UTC, datetime

    issues = FakeGitHubIssues(
        issues={
            42: IssueInfo(
                number=42,
                title="Test Issue",
                body="Test body",
                state="OPEN",
                url="https://github.com/owner/repo/issues/42",
                labels=["erk-plan"],
                assignees=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                author="test-user",
            )
        }
    )

    # Post comment
    add_worktree_creation_comment(issues, tmp_path, 42, "feature-name", "feature-branch")

    # Verify comment was added
    assert len(issues.added_comments) == 1
    issue_number, comment_body, _comment_id = issues.added_comments[0]

    # Verify comment details
    assert issue_number == 42
    assert "✅ Worktree created: **feature-name**" in comment_body
    assert "erk br co feature-branch" in comment_body
    assert "/erk:plan-implement" in comment_body

    # Round-trip verification: Parse metadata block back out
    blocks = parse_metadata_blocks(comment_body)
    assert len(blocks) == 1

    block = find_metadata_block(comment_body, "erk-worktree-creation")
    assert block is not None
    assert block.key == "erk-worktree-creation"
    assert block.data["worktree_name"] == "feature-name"
    assert block.data["branch_name"] == "feature-branch"
    assert block.data["issue_number"] == 42
    assert "timestamp" in block.data
    assert isinstance(block.data["timestamp"], str)
    assert len(block.data["timestamp"]) > 0

    # Verify timestamp format (ISO 8601 UTC)
    assert "T" in block.data["timestamp"]  # ISO 8601 includes 'T' separator
    assert ":" in block.data["timestamp"]  # ISO 8601 includes ':' in time


def test_add_worktree_creation_comment_issue_not_found(tmp_path: Path) -> None:
    """Test add_worktree_creation_comment raises error when issue doesn't exist."""
    issues = FakeGitHubIssues(issues={})  # No issues

    # Should raise RuntimeError (simulating gh CLI error)
    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        add_worktree_creation_comment(issues, tmp_path, 999, "feature-name", "feature-branch")


# ============================================================================
# Plan Author Attribution Tests
# ============================================================================


def test_read_plan_author_success(tmp_path: Path) -> None:
    """Test reading plan author from plan.md with valid plan-header block."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md with plan-header metadata block
    plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: test-user
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan

1. Step one
2. Step two
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Read author
    author = read_plan_author(impl_dir)

    assert author == "test-user"


def test_read_plan_author_no_plan_file(tmp_path: Path) -> None:
    """Test read_plan_author returns None when plan.md doesn't exist."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    author = read_plan_author(impl_dir)

    assert author is None


def test_read_plan_author_no_impl_dir(tmp_path: Path) -> None:
    """Test read_plan_author returns None when .impl/ directory doesn't exist."""
    impl_dir = tmp_path / ".impl"
    # Don't create the directory

    author = read_plan_author(impl_dir)

    assert author is None


def test_read_plan_author_no_metadata_block(tmp_path: Path) -> None:
    """Test read_plan_author returns None when plan.md has no plan-header block."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md without metadata block
    plan_content = """# Simple Plan

1. Step one
2. Step two
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    author = read_plan_author(impl_dir)

    assert author is None


def test_read_plan_author_missing_created_by_field(tmp_path: Path) -> None:
    """Test read_plan_author returns None when created_by field is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md with plan-header but no created_by
    plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    author = read_plan_author(impl_dir)

    assert author is None


# ============================================================================
# Last Dispatched Run ID Tests
# ============================================================================


def test_read_last_dispatched_run_id_success(tmp_path: Path) -> None:
    """Test reading run ID from plan.md with valid plan-header block."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md with plan-header metadata block including run ID
    plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: test-user
worktree_name: test-worktree
last_dispatched_run_id: '12345678901'
last_dispatched_at: '2025-01-15T11:00:00+00:00'

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan

1. Step one
2. Step two
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Read run ID
    run_id = read_last_dispatched_run_id(impl_dir)

    assert run_id == "12345678901"


def test_read_last_dispatched_run_id_no_plan_file(tmp_path: Path) -> None:
    """Test read_last_dispatched_run_id returns None when plan.md doesn't exist."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    run_id = read_last_dispatched_run_id(impl_dir)

    assert run_id is None


def test_read_last_dispatched_run_id_no_impl_dir(tmp_path: Path) -> None:
    """Test read_last_dispatched_run_id returns None when .impl/ directory doesn't exist."""
    impl_dir = tmp_path / ".impl"
    # Don't create the directory

    run_id = read_last_dispatched_run_id(impl_dir)

    assert run_id is None


def test_read_last_dispatched_run_id_no_metadata_block(tmp_path: Path) -> None:
    """Test read_last_dispatched_run_id returns None when plan.md has no plan-header block."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md without metadata block
    plan_content = """# Simple Plan

1. Step one
2. Step two
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    run_id = read_last_dispatched_run_id(impl_dir)

    assert run_id is None


def test_read_last_dispatched_run_id_null_value(tmp_path: Path) -> None:
    """Test read_last_dispatched_run_id returns None when run ID is null."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md with plan-header but null run ID
    plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: test-user
worktree_name: test-worktree
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    run_id = read_last_dispatched_run_id(impl_dir)

    assert run_id is None


def test_read_last_dispatched_run_id_missing_field(tmp_path: Path) -> None:
    """Test read_last_dispatched_run_id returns None when run ID field is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md with plan-header but no last_dispatched_run_id
    plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-01-15T10:00:00+00:00'
created_by: test-user
worktree_name: test-worktree

```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
    plan_file = impl_dir / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    run_id = read_last_dispatched_run_id(impl_dir)

    assert run_id is None


# ============================================================================
# Progress Schema Validation Tests
# ============================================================================


def test_validate_progress_schema_valid_file(tmp_path: Path) -> None:
    """Test validation passes for valid progress.md."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 1
completed_steps: 1
total_steps: 3
steps:
  - number: 1
    title: 'First step'
    completed: true
  - number: 2
    title: 'Second step'
    completed: false
  - number: 3
    title: 'Third step'
    completed: false
---

# Progress Tracking
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert errors == []


def test_validate_progress_schema_empty_steps(tmp_path: Path) -> None:
    """Test validation passes for progress.md with empty steps array."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 0
completed_steps: 0
total_steps: 0
steps: []
---

# Progress Tracking

No steps detected in plan.
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert errors == []


def test_validate_progress_schema_file_not_found(tmp_path: Path) -> None:
    """Test validation fails for missing file."""
    progress_file = tmp_path / "progress.md"

    errors = validate_progress_schema(progress_file)

    assert errors == ["progress.md file not found"]


def test_validate_progress_schema_invalid_yaml(tmp_path: Path) -> None:
    """Test validation fails for invalid YAML."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
steps: [invalid yaml
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert len(errors) == 1
    assert "Invalid YAML" in errors[0]


def test_validate_progress_schema_missing_steps_field(tmp_path: Path) -> None:
    """Test validation fails when steps field is missing."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
completed_steps: 0
total_steps: 0
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Missing 'steps' field" in errors


def test_validate_progress_schema_steps_not_list(tmp_path: Path) -> None:
    """Test validation fails when steps is not a list."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
completed_steps: 0
total_steps: 0
steps: "not a list"
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "'steps' must be a list" in errors


def test_validate_progress_schema_step_missing_number(tmp_path: Path) -> None:
    """Test validation fails when step is missing number field."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 0
completed_steps: 0
total_steps: 1
steps:
  - title: 'Step one'
    completed: false
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Step 1 missing 'number' field" in errors


def test_validate_progress_schema_step_missing_title(tmp_path: Path) -> None:
    """Test validation fails when step is missing title field."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 0
completed_steps: 0
total_steps: 1
steps:
  - number: 1
    completed: false
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Step 1 missing 'title' field" in errors


def test_validate_progress_schema_step_missing_completed(tmp_path: Path) -> None:
    """Test validation fails when step is missing completed field."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 0
completed_steps: 0
total_steps: 1
steps:
  - number: 1
    title: 'Step one'
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Step 1 missing 'completed' field" in errors


def test_validate_progress_schema_missing_total_steps(tmp_path: Path) -> None:
    """Test validation fails when total_steps is missing."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
completed_steps: 0
steps: []
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Missing 'total_steps' field" in errors


def test_validate_progress_schema_missing_completed_steps(tmp_path: Path) -> None:
    """Test validation fails when completed_steps is missing."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
total_steps: 0
steps: []
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Missing 'completed_steps' field" in errors


def test_validate_progress_schema_total_steps_mismatch(tmp_path: Path) -> None:
    """Test validation fails when total_steps doesn't match len(steps)."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 0
completed_steps: 0
total_steps: 5
steps:
  - number: 1
    title: 'Step one'
    completed: false
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert len(errors) == 1
    assert "total_steps (5) != len(steps) (1)" in errors[0]


def test_validate_progress_schema_completed_steps_mismatch(tmp_path: Path) -> None:
    """Test validation fails when completed_steps doesn't match actual count."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
current_step: 0
completed_steps: 2
total_steps: 2
steps:
  - number: 1
    title: 'Step one'
    completed: true
  - number: 2
    title: 'Step two'
    completed: false
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert len(errors) == 1
    assert "completed_steps (2) != actual count (1)" in errors[0]


def test_validate_progress_schema_step_not_object(tmp_path: Path) -> None:
    """Test validation fails when step is not an object."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """---
completed_steps: 0
total_steps: 1
steps:
  - "just a string"
---

# Progress
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    assert "Step 1 must be an object" in errors


def test_validate_progress_schema_no_frontmatter(tmp_path: Path) -> None:
    """Test validation fails when file has no YAML frontmatter."""
    progress_file = tmp_path / "progress.md"
    progress_file.write_text(
        """# Progress Tracking

No steps detected in plan.
""",
        encoding="utf-8",
    )

    errors = validate_progress_schema(progress_file)

    # Without frontmatter, frontmatter.loads returns empty metadata
    assert "Missing 'steps' field" in errors
    assert "Missing 'total_steps' field" in errors
    assert "Missing 'completed_steps' field" in errors


# ============================================================================
# Issue Linkage Validation Tests
# ============================================================================


def test_validate_issue_linkage_both_match(tmp_path: Path) -> None:
    """Test validation passes when branch and .impl/issue.json match."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_issue_reference(impl_dir, 42, "https://github.com/org/repo/issues/42")

    # Branch name matches issue number
    result = validate_issue_linkage(impl_dir, "P42-add-feature-01-04-1234")

    assert result == 42


def test_validate_issue_linkage_mismatch_raises(tmp_path: Path) -> None:
    """Test validation raises ValueError when branch and .impl/issue.json disagree."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_issue_reference(impl_dir, 99, "https://github.com/org/repo/issues/99")

    # Branch says issue 42, but .impl/ says issue 99
    with pytest.raises(ValueError) as exc_info:
        validate_issue_linkage(impl_dir, "P42-add-feature-01-04-1234")

    error_msg = str(exc_info.value)
    assert "P42" in error_msg
    assert "#99" in error_msg
    assert "disagrees" in error_msg


def test_validate_issue_linkage_branch_only(tmp_path: Path) -> None:
    """Test validation returns branch issue when no .impl/ exists."""
    impl_dir = tmp_path / ".impl"
    # Don't create impl_dir

    result = validate_issue_linkage(impl_dir, "P123-some-feature-01-04-1234")

    assert result == 123


def test_validate_issue_linkage_impl_only(tmp_path: Path) -> None:
    """Test validation returns impl issue when branch has no issue number."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_issue_reference(impl_dir, 456, "https://github.com/org/repo/issues/456")

    # Branch without issue prefix (e.g., main, master, feature-branch)
    result = validate_issue_linkage(impl_dir, "main")

    assert result == 456


def test_validate_issue_linkage_neither(tmp_path: Path) -> None:
    """Test validation returns None when neither source has issue number."""
    impl_dir = tmp_path / ".impl"
    # Don't create impl_dir

    # Branch without issue prefix
    result = validate_issue_linkage(impl_dir, "feature-branch")

    assert result is None


def test_validate_issue_linkage_impl_exists_no_issue_json(tmp_path: Path) -> None:
    """Test validation uses branch when .impl/ exists but has no issue.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    # Create plan.md but NOT issue.json
    (impl_dir / "plan.md").write_text("# Plan", encoding="utf-8")

    result = validate_issue_linkage(impl_dir, "P789-feature-01-04-1234")

    assert result == 789


def test_validate_issue_linkage_worker_impl(tmp_path: Path) -> None:
    """Test validation works with .worker-impl/ folder."""
    worker_impl_dir = tmp_path / ".worker-impl"
    worker_impl_dir.mkdir()
    save_issue_reference(worker_impl_dir, 555, "https://github.com/org/repo/issues/555")

    result = validate_issue_linkage(worker_impl_dir, "P555-worker-feature-01-04-1234")

    assert result == 555
