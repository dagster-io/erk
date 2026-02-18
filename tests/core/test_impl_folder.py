"""Tests for implementation folder management utilities."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata_blocks import (
    find_metadata_block,
    parse_metadata_blocks,
)
from erk_shared.impl_folder import (
    add_worktree_creation_comment,
    create_impl_folder,
    get_impl_path,
    has_plan_ref,
    read_last_dispatched_run_id,
    read_plan_author,
    read_plan_ref,
    save_plan_ref,
    validate_plan_linkage,
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
# PlanRef Storage Tests
# ============================================================================


def test_save_plan_ref_success(tmp_path: Path) -> None:
    """Test saving plan reference to .impl/plan-ref.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="42",
        url="https://github.com/owner/repo/issues/42",
        labels=("erk-plan",),
        objective_id=99,
    )

    plan_ref_file = impl_dir / "plan-ref.json"
    assert plan_ref_file.exists()

    data = json.loads(plan_ref_file.read_text(encoding="utf-8"))
    assert data["provider"] == "github"
    assert data["plan_id"] == "42"
    assert data["url"] == "https://github.com/owner/repo/issues/42"
    assert data["labels"] == ["erk-plan"]
    assert data["objective_id"] == 99
    assert "created_at" in data
    assert "synced_at" in data


def test_save_plan_ref_dir_not_exists(tmp_path: Path) -> None:
    """Test save_plan_ref raises error when dir doesn't exist."""
    impl_dir = tmp_path / ".impl"

    with pytest.raises(FileNotFoundError, match="Implementation directory does not exist"):
        save_plan_ref(
            impl_dir,
            provider="github",
            plan_id="42",
            url="http://url",
            labels=(),
            objective_id=None,
        )


def test_save_plan_ref_no_objective(tmp_path: Path) -> None:
    """Test save_plan_ref stores null for objective_id when None."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="42",
        url="http://url",
        labels=(),
        objective_id=None,
    )

    data = json.loads((impl_dir / "plan-ref.json").read_text(encoding="utf-8"))
    assert data["objective_id"] is None


def test_read_plan_ref_roundtrip(tmp_path: Path) -> None:
    """Test save -> read roundtrip for plan-ref.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="42",
        url="https://github.com/owner/repo/issues/42",
        labels=("erk-plan", "erk-learn"),
        objective_id=99,
    )

    ref = read_plan_ref(impl_dir)
    assert ref is not None
    assert ref.provider == "github"
    assert ref.plan_id == "42"
    assert ref.url == "https://github.com/owner/repo/issues/42"
    assert ref.labels == ("erk-plan", "erk-learn")
    assert ref.objective_id == 99
    assert len(ref.created_at) > 0
    assert len(ref.synced_at) > 0


def test_read_plan_ref_from_legacy_issue_json(tmp_path: Path) -> None:
    """Test read_plan_ref falls back to legacy issue.json format."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Write legacy issue.json (no plan-ref.json)
    issue_data = {
        "issue_number": 42,
        "issue_url": "https://github.com/owner/repo/issues/42",
        "created_at": "2025-01-15T10:00:00+00:00",
        "synced_at": "2025-01-15T10:00:00+00:00",
        "labels": ["erk-plan"],
        "objective_issue": 99,
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_data), encoding="utf-8")

    ref = read_plan_ref(impl_dir)
    assert ref is not None
    assert ref.provider == "github"
    assert ref.plan_id == "42"
    assert ref.url == "https://github.com/owner/repo/issues/42"
    assert ref.labels == ("erk-plan",)
    assert ref.objective_id == 99


def test_read_plan_ref_prefers_plan_ref_json(tmp_path: Path) -> None:
    """Test read_plan_ref prefers plan-ref.json over legacy issue.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Write both files with different data
    plan_ref_data = {
        "provider": "linear",
        "plan_id": "PROJ-123",
        "url": "https://linear.app/proj/PROJ-123",
        "created_at": "2025-01-15T10:00:00+00:00",
        "synced_at": "2025-01-15T10:00:00+00:00",
        "labels": [],
        "objective_id": None,
    }
    (impl_dir / "plan-ref.json").write_text(json.dumps(plan_ref_data), encoding="utf-8")

    issue_data = {
        "issue_number": 42,
        "issue_url": "https://github.com/owner/repo/issues/42",
        "created_at": "2025-01-15T10:00:00+00:00",
        "synced_at": "2025-01-15T10:00:00+00:00",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_data), encoding="utf-8")

    ref = read_plan_ref(impl_dir)
    assert ref is not None
    assert ref.provider == "linear"
    assert ref.plan_id == "PROJ-123"


def test_read_plan_ref_not_exists(tmp_path: Path) -> None:
    """Test read_plan_ref returns None when no files exist."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    ref = read_plan_ref(impl_dir)
    assert ref is None


def test_read_plan_ref_invalid_json(tmp_path: Path) -> None:
    """Test read_plan_ref returns None for invalid JSON."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    (impl_dir / "plan-ref.json").write_text("not valid json", encoding="utf-8")

    ref = read_plan_ref(impl_dir)
    assert ref is None


def test_read_plan_ref_missing_fields(tmp_path: Path) -> None:
    """Test read_plan_ref returns None when required fields missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    (impl_dir / "plan-ref.json").write_text(json.dumps({"provider": "github"}), encoding="utf-8")

    ref = read_plan_ref(impl_dir)
    assert ref is None


def test_has_plan_ref_with_plan_ref_json(tmp_path: Path) -> None:
    """Test has_plan_ref detects plan-ref.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="42",
        url="http://url",
        labels=(),
        objective_id=None,
    )

    assert has_plan_ref(impl_dir) is True


def test_has_plan_ref_detects_legacy_file(tmp_path: Path) -> None:
    """Test has_plan_ref detects legacy issue.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Write only legacy issue.json file
    legacy_data = {
        "issue_number": 42,
        "issue_url": "http://url",
        "created_at": "2025-01-15T10:00:00+00:00",
        "synced_at": "2025-01-15T10:00:00+00:00",
    }
    (impl_dir / "issue.json").write_text(json.dumps(legacy_data), encoding="utf-8")

    assert has_plan_ref(impl_dir) is True


def test_has_plan_ref_not_exists(tmp_path: Path) -> None:
    """Test has_plan_ref returns False when neither file exists."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    assert has_plan_ref(impl_dir) is False


# ============================================================================
# Plan Linkage Validation Tests (PlanRef-based)
# ============================================================================


def test_validate_plan_linkage_both_match(tmp_path: Path) -> None:
    """Test validation passes when branch and plan-ref.json match."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="42",
        url="https://github.com/org/repo/issues/42",
        labels=(),
        objective_id=None,
    )

    result = validate_plan_linkage(impl_dir, "P42-add-feature-01-04-1234")
    assert result == "42"


def test_validate_plan_linkage_mismatch_raises(tmp_path: Path) -> None:
    """Test validation raises ValueError when branch and plan ref disagree."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="99",
        url="https://github.com/org/repo/issues/99",
        labels=(),
        objective_id=None,
    )

    with pytest.raises(ValueError) as exc_info:
        validate_plan_linkage(impl_dir, "P42-add-feature-01-04-1234")

    error_msg = str(exc_info.value)
    assert "42" in error_msg
    assert "#99" in error_msg
    assert "disagrees" in error_msg


def test_validate_plan_linkage_branch_only(tmp_path: Path) -> None:
    """Test validation returns branch issue as string when no plan ref exists."""
    impl_dir = tmp_path / ".impl"

    result = validate_plan_linkage(impl_dir, "P123-some-feature-01-04-1234")
    assert result == "123"


def test_validate_plan_linkage_impl_only(tmp_path: Path) -> None:
    """Test validation returns plan_id when branch has no issue number."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id="456",
        url="https://github.com/org/repo/issues/456",
        labels=(),
        objective_id=None,
    )

    result = validate_plan_linkage(impl_dir, "main")
    assert result == "456"


def test_validate_plan_linkage_neither(tmp_path: Path) -> None:
    """Test validation returns None when neither source has info."""
    impl_dir = tmp_path / ".impl"

    result = validate_plan_linkage(impl_dir, "feature-branch")
    assert result is None


def test_validate_plan_linkage_legacy_fallback(tmp_path: Path) -> None:
    """Test validation works with legacy issue.json via read_plan_ref fallback."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    legacy_data = {
        "issue_number": 42,
        "issue_url": "https://github.com/org/repo/issues/42",
        "created_at": "2025-01-15T10:00:00+00:00",
        "synced_at": "2025-01-15T10:00:00+00:00",
    }
    (impl_dir / "issue.json").write_text(json.dumps(legacy_data), encoding="utf-8")

    result = validate_plan_linkage(impl_dir, "P42-add-feature-01-04-1234")
    assert result == "42"


def test_validate_plan_linkage_draft_pr_with_plan_ref(tmp_path: Path) -> None:
    """Test draft-PR branch returns plan_id from plan-ref.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    save_plan_ref(
        impl_dir,
        provider="github-draft-pr",
        plan_id="789",
        url="https://github.com/org/repo/pull/789",
        labels=(),
        objective_id=None,
    )

    result = validate_plan_linkage(impl_dir, "plan-fix-auth-bug-01-15-1430")
    assert result == "789"


def test_validate_plan_linkage_draft_pr_without_plan_ref(tmp_path: Path) -> None:
    """Test draft-PR branch without plan-ref.json returns None."""
    impl_dir = tmp_path / ".impl"

    result = validate_plan_linkage(impl_dir, "plan-fix-auth-bug-01-15-1430")
    assert result is None
