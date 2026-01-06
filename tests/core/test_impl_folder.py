"""Tests for implementation folder management utilities."""

import json
from datetime import UTC, datetime
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
    get_impl_path,
    has_issue_reference,
    read_issue_reference,
    read_last_dispatched_run_id,
    read_plan_author,
    save_issue_reference,
    validate_issue_linkage,
)

# =============================================================================
# create_impl_folder Tests
# =============================================================================


def test_create_impl_folder_basic(tmp_path: Path) -> None:
    """Test creating an impl folder with basic plan content."""
    plan_content = """# Implementation Plan: Test Feature

## Objective
Build a test feature.

## Tasks
1. Create module
2. Add tests
3. Update documentation
"""
    plan_folder = create_impl_folder(tmp_path, plan_content, overwrite=False)

    # Verify folder structure
    assert plan_folder.exists()
    assert plan_folder == tmp_path / ".impl"

    # Verify plan.md exists and has correct content
    plan_file = plan_folder / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content


def test_create_impl_folder_already_exists(tmp_path: Path) -> None:
    """Test that creating a plan folder when one exists raises error."""
    plan_content = "# Test Plan\n"

    # Create first time - should succeed
    create_impl_folder(tmp_path, plan_content, overwrite=False)

    # Try to create again - should raise
    with pytest.raises(FileExistsError, match="Implementation folder already exists"):
        create_impl_folder(tmp_path, plan_content, overwrite=False)


def test_create_impl_folder_overwrite_replaces_existing(tmp_path: Path) -> None:
    """Test that overwrite=True removes existing .impl/ folder before creating new one.

    This is the fix for GitHub issue #2595 where creating a worktree from a branch
    with an existing .impl/ folder would fail because the folder was inherited.
    """
    old_plan = "# Old Plan\n\nOld content.\n"
    new_plan = "# New Plan\n\nNew content.\n"

    # Create first .impl/ folder
    impl_folder = create_impl_folder(tmp_path, old_plan, overwrite=False)
    old_plan_file = impl_folder / "plan.md"

    # Verify old content
    assert old_plan_file.read_text(encoding="utf-8") == old_plan

    # Create again with overwrite=True - should succeed and replace content
    new_impl_folder = create_impl_folder(tmp_path, new_plan, overwrite=True)

    # Verify new content replaced old
    assert new_impl_folder == impl_folder  # Same path
    new_plan_file = new_impl_folder / "plan.md"

    assert new_plan_file.read_text(encoding="utf-8") == new_plan

    # Verify old content is gone
    assert "Old" not in new_plan_file.read_text(encoding="utf-8")


def test_get_impl_path_exists(tmp_path: Path) -> None:
    """Test getting plan path when it exists."""
    plan_content = "# Test\n"
    create_impl_folder(tmp_path, plan_content, overwrite=False)

    plan_path = get_impl_path(tmp_path)
    assert plan_path is not None
    assert plan_path == tmp_path / ".impl" / "plan.md"
    assert plan_path.exists()


def test_get_impl_path_not_exists(tmp_path: Path) -> None:
    """Test getting plan path when it doesn't exist."""
    plan_path = get_impl_path(tmp_path)
    assert plan_path is None


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
    plan_content = "# Test Plan\n"
    plan_folder = create_impl_folder(tmp_path, plan_content, overwrite=False)

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
    add_worktree_creation_comment(
        github_issues=issues,
        repo_root=tmp_path,
        issue_number=42,
        worktree_name="feature-name",
        branch_name="feature-branch",
    )

    # Verify comment was added
    assert len(issues.added_comments) == 1
    issue_number, comment_body, _comment_id = issues.added_comments[0]

    # Verify comment details
    assert issue_number == 42
    assert "✅ Worktree created: **feature-name**" in comment_body
    assert "erk br co feature-branch" in comment_body
    assert "/erk:system:impl-execute" in comment_body

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
        add_worktree_creation_comment(
            github_issues=issues,
            repo_root=tmp_path,
            issue_number=999,
            worktree_name="feature-name",
            branch_name="feature-branch",
        )


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
