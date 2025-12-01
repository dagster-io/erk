"""Tests for implementation folder management utilities."""

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
    extract_steps_from_plan,
    get_impl_path,
    get_progress_path,
    has_issue_reference,
    parse_progress_frontmatter,
    read_issue_reference,
    read_last_dispatched_run_id,
    read_plan_author,
    save_issue_reference,
    update_progress,
    update_progress_frontmatter,
)


def test_create_impl_folder_basic(tmp_path: Path) -> None:
    """Test creating a plan folder with basic plan content."""
    plan_content = """# Implementation Plan: Test Feature

## Objective
Build a test feature.

## Implementation Steps

1. Create module
2. Add tests
3. Update documentation
"""

    plan_folder = create_impl_folder(tmp_path, plan_content)

    # Verify folder structure
    assert plan_folder.exists()
    assert plan_folder == tmp_path / ".impl"

    # Verify plan.md exists and has correct content
    plan_file = plan_folder / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content

    # Verify progress.md exists and has checkboxes
    progress_file = plan_folder / "progress.md"
    assert progress_file.exists()
    progress_content = progress_file.read_text(encoding="utf-8")
    assert "- [ ] 1. Create module" in progress_content
    assert "- [ ] 2. Add tests" in progress_content
    assert "- [ ] 3. Update documentation" in progress_content


def test_create_impl_folder_already_exists(tmp_path: Path) -> None:
    """Test that creating a plan folder when one exists raises error."""
    plan_content = "# Test Plan\n\n1. Step one"

    # Create first time - should succeed
    create_impl_folder(tmp_path, plan_content)

    # Try to create again - should raise
    with pytest.raises(FileExistsError, match="Implementation folder already exists"):
        create_impl_folder(tmp_path, plan_content)


def test_create_impl_folder_with_nested_steps(tmp_path: Path) -> None:
    """Test creating plan folder with nested step numbering."""
    plan_content = """# Complex Plan

## Phase 1

1. Main step one
1.1. Substep one
1.2. Substep two

2. Main step two
2.1. Substep one
2.2. Substep two
2.3. Substep three
"""

    plan_folder = create_impl_folder(tmp_path, plan_content)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify all steps are in progress.md
    assert "- [ ] 1. Main step one" in progress_content
    assert "- [ ] 1.1. Substep one" in progress_content
    assert "- [ ] 1.2. Substep two" in progress_content
    assert "- [ ] 2. Main step two" in progress_content
    assert "- [ ] 2.1. Substep one" in progress_content
    assert "- [ ] 2.2. Substep two" in progress_content
    assert "- [ ] 2.3. Substep three" in progress_content


def test_create_impl_folder_empty_plan(tmp_path: Path) -> None:
    """Test creating plan folder with empty or no-steps plan."""
    plan_content = """# Empty Plan

This plan has no numbered steps.
Just some text.
"""

    plan_folder = create_impl_folder(tmp_path, plan_content)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Should create progress.md with message about no steps
    assert progress_file.exists()
    assert "No steps detected" in progress_content


def test_get_impl_path_exists(tmp_path: Path) -> None:
    """Test getting plan path when it exists."""
    plan_content = "# Test\n\n1. Step"
    create_impl_folder(tmp_path, plan_content)

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
    plan_content = "# Test\n\n1. Step"
    create_impl_folder(tmp_path, plan_content)

    progress_path = get_progress_path(tmp_path)
    assert progress_path is not None
    assert progress_path == tmp_path / ".impl" / "progress.md"
    assert progress_path.exists()


def test_get_progress_path_not_exists(tmp_path: Path) -> None:
    """Test getting progress path when it doesn't exist."""
    progress_path = get_progress_path(tmp_path)
    assert progress_path is None


def test_update_progress(tmp_path: Path) -> None:
    """Test updating progress.md content."""
    plan_content = "# Test\n\n1. Step one\n2. Step two"
    create_impl_folder(tmp_path, plan_content)

    # Update progress with completed first step
    new_progress = """# Progress Tracking

- [x] 1. Step one
- [ ] 2. Step two
"""
    update_progress(tmp_path, new_progress)

    # Verify update
    progress_file = tmp_path / ".impl" / "progress.md"
    assert progress_file.read_text(encoding="utf-8") == new_progress


def test_extract_steps_numbered_with_period(tmp_path: Path) -> None:
    """Test extracting steps with '1.' format."""
    plan = """# Plan

1. First step
2. Second step
3. Third step
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 3
    assert "1. First step" in steps
    assert "2. Second step" in steps
    assert "3. Third step" in steps


def test_extract_steps_numbered_with_paren(tmp_path: Path) -> None:
    """Test extracting steps with '1)' format."""
    plan = """# Plan

1) First step
2) Second step
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert "1) First step" in steps
    assert "2) Second step" in steps


def test_extract_steps_with_step_word(tmp_path: Path) -> None:
    """Test extracting steps with 'Step X:' format."""
    plan = """# Plan

Step 1: First step
Step 2: Second step
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert "Step 1: First step" in steps
    assert "Step 2: Second step" in steps


def test_extract_steps_nested_numbering(tmp_path: Path) -> None:
    """Test extracting steps with nested numbering."""
    plan = """# Plan

1. Main step
1.1. Substep A
1.2. Substep B
2. Another main step
2.1. Substep C
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 5
    assert "1. Main step" in steps
    assert "1.1. Substep A" in steps
    assert "1.2. Substep B" in steps
    assert "2. Another main step" in steps
    assert "2.1. Substep C" in steps


def test_extract_steps_mixed_formats(tmp_path: Path) -> None:
    """Test extracting steps from plan with mixed formats."""
    plan = """# Plan

1. First format
2) Second format
Step 3: Third format
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 3


def test_extract_steps_ignores_non_steps(tmp_path: Path) -> None:
    """Test that extraction ignores non-step content."""
    plan = """# Plan

This is intro text.

1. Actual step
2. Another step

Some more text that isn't a step.
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert "1. Actual step" in steps
    assert "2. Another step" in steps


def test_extract_steps_empty_plan(tmp_path: Path) -> None:
    """Test extracting steps from plan with no steps."""
    plan = """# Plan

Just text, no steps.
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 0


def test_extract_steps_indented_steps(tmp_path: Path) -> None:
    """Test extracting indented steps."""
    plan = """# Plan

   1. Indented step
     2. More indented
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 2
    assert any("1. Indented step" in s for s in steps)
    assert any("2. More indented" in s for s in steps)


def test_extract_steps_with_special_characters(tmp_path: Path) -> None:
    """Test extracting steps with special characters in descriptions."""
    plan = """# Plan

1. Step with **bold** and *italic*
2. Step with `code` and [link](url)
3. Step with emoji 🎉
"""
    steps = extract_steps_from_plan(plan)
    assert len(steps) == 3
    # Steps should preserve the full line including special characters
    assert any("**bold**" in s for s in steps)
    assert any("`code`" in s for s in steps)
    assert any("🎉" in s for s in steps)


def test_create_impl_folder_generates_frontmatter(tmp_path: Path) -> None:
    """Test that creating a plan folder generates YAML front matter in progress.md."""
    plan_content = """# Test Plan

1. First step
2. Second step
3. Third step
"""
    plan_folder = create_impl_folder(tmp_path, plan_content)
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

1. First step
2. Second step
3. Third step
"""
    plan_folder = create_impl_folder(tmp_path, plan_content)
    progress_file = plan_folder / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Parse frontmatter to verify steps array
    metadata = parse_progress_frontmatter(progress_content)
    assert metadata is not None
    assert "steps" in metadata
    assert isinstance(metadata["steps"], list)
    assert len(metadata["steps"]) == 3

    # Verify each step has text and completed fields
    for step in metadata["steps"]:
        assert "text" in step
        assert "completed" in step
        assert isinstance(step["completed"], bool)
        assert step["completed"] is False  # All start uncompleted

    # Verify step texts
    assert metadata["steps"][0]["text"] == "1. First step"
    assert metadata["steps"][1]["text"] == "2. Second step"
    assert metadata["steps"][2]["text"] == "3. Third step"


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


def test_update_progress_frontmatter_replaces_existing(tmp_path: Path) -> None:
    """Test updating existing front matter preserves checkbox content."""
    plan_content = "# Test\n\n1. Step one\n2. Step two"
    create_impl_folder(tmp_path, plan_content)

    # Manually mark first checkbox as completed
    progress_file = tmp_path / ".impl" / "progress.md"
    content = progress_file.read_text(encoding="utf-8")
    content = content.replace("- [ ] 1. Step one", "- [x] 1. Step one")
    progress_file.write_text(content, encoding="utf-8")

    # Update front matter to reflect 1/2 completed
    update_progress_frontmatter(tmp_path, 1, 2)

    # Verify front matter updated
    updated_content = progress_file.read_text(encoding="utf-8")
    assert "completed_steps: 1" in updated_content
    assert "total_steps: 2" in updated_content

    # Verify checkboxes preserved
    assert "- [x] 1. Step one" in updated_content
    assert "- [ ] 2. Step two" in updated_content


def test_update_progress_frontmatter_adds_if_missing(tmp_path: Path) -> None:
    """Test adding front matter to file that doesn't have it."""
    # Create progress file without front matter
    plan_folder = tmp_path / ".impl"
    plan_folder.mkdir()
    progress_file = plan_folder / "progress.md"
    progress_file.write_text(
        """# Progress Tracking

- [x] 1. Step one
- [ ] 2. Step two
""",
        encoding="utf-8",
    )

    # Add front matter
    update_progress_frontmatter(tmp_path, 1, 2)

    # Verify front matter added
    updated_content = progress_file.read_text(encoding="utf-8")
    assert updated_content.startswith("---\n")
    assert "completed_steps: 1" in updated_content
    assert "total_steps: 2" in updated_content

    # Verify checkboxes preserved
    assert "- [x] 1. Step one" in updated_content
    assert "- [ ] 2. Step two" in updated_content


def test_update_progress_frontmatter_no_file(tmp_path: Path) -> None:
    """Test updating front matter when file doesn't exist does nothing."""
    # Should not raise error
    update_progress_frontmatter(tmp_path, 1, 2)


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
    plan_content = "# Test Plan\n\n1. Step one"
    plan_folder = create_impl_folder(tmp_path, plan_content)

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
            )
        }
    )

    # Post comment
    add_worktree_creation_comment(issues, tmp_path, 42, "feature-name", "feature-branch")

    # Verify comment was added
    assert len(issues.added_comments) == 1
    issue_number, comment_body = issues.added_comments[0]

    # Verify comment details
    assert issue_number == 42
    assert "✅ Worktree created: **feature-name**" in comment_body
    assert "erk checkout feature-branch" in comment_body
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
