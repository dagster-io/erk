"""Tests for impl_context utilities.

Layer 3: Pure unit tests (zero dependencies).

These tests verify the impl_context module functions work correctly with
basic filesystem operations.
"""

import json
from pathlib import Path

import pytest


def test_create_impl_context_success(tmp_path: Path) -> None:
    """Test creating .erk/impl-context/ folder with all required files."""
    from erk_shared.impl_context import create_impl_context

    plan_content = "# Test Plan\n\n## Tasks\n\n1. First task\n2. Second task\n"

    impl_context_dir = create_impl_context(
        plan_content=plan_content,
        plan_id="123",
        url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
        provider="github",
        objective_id=None,
    )

    # Verify folder was created
    assert impl_context_dir == tmp_path / ".erk" / "impl-context"
    assert impl_context_dir.exists()
    assert impl_context_dir.is_dir()

    # Verify plan.md exists with correct content
    plan_file = impl_context_dir / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content

    # Verify ref.json exists with correct structure
    ref_file = impl_context_dir / "ref.json"
    assert ref_file.exists()
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))
    assert ref_data["provider"] == "github"
    assert ref_data["plan_id"] == "123"
    assert ref_data["url"] == "https://github.com/owner/repo/issues/123"
    assert "created_at" in ref_data
    assert "synced_at" in ref_data


def test_create_impl_context_already_exists(tmp_path: Path) -> None:
    """Test error when .erk/impl-context/ folder already exists."""
    from erk_shared.impl_context import create_impl_context

    # Create .erk/impl-context/ folder first
    impl_context_dir = tmp_path / ".erk" / "impl-context"
    impl_context_dir.mkdir(parents=True)

    # Attempt to create again should raise FileExistsError
    with pytest.raises(FileExistsError, match=".erk/impl-context/ folder already exists"):
        create_impl_context(
            plan_content="# Test",
            plan_id="123",
            url="https://github.com/owner/repo/issues/123",
            repo_root=tmp_path,
            provider="github",
            objective_id=None,
        )


def test_create_impl_context_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo_root doesn't exist."""
    from erk_shared.impl_context import create_impl_context

    nonexistent_path = tmp_path / "nonexistent"

    with pytest.raises(ValueError, match="Repository root does not exist"):
        create_impl_context(
            plan_content="# Test",
            plan_id="123",
            url="https://github.com/owner/repo/issues/123",
            repo_root=nonexistent_path,
            provider="github",
            objective_id=None,
        )


def test_create_impl_context_repo_root_not_directory(tmp_path: Path) -> None:
    """Test error when repo_root is a file, not a directory."""
    from erk_shared.impl_context import create_impl_context

    # Create a file, not a directory
    file_path = tmp_path / "file.txt"
    file_path.write_text("test", encoding="utf-8")

    with pytest.raises(ValueError, match="Repository root is not a directory"):
        create_impl_context(
            plan_content="# Test",
            plan_id="123",
            url="https://github.com/owner/repo/issues/123",
            repo_root=file_path,
            provider="github",
            objective_id=None,
        )


def test_remove_impl_context_success(tmp_path: Path) -> None:
    """Test removing .erk/impl-context/ folder."""
    from erk_shared.impl_context import create_impl_context, remove_impl_context

    # Create .erk/impl-context/ folder first
    create_impl_context(
        plan_content="# Test\n",
        plan_id="123",
        url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
        provider="github",
        objective_id=None,
    )

    impl_context_dir = tmp_path / ".erk" / "impl-context"
    assert impl_context_dir.exists()

    # Remove it
    remove_impl_context(tmp_path)

    # Verify it's gone
    assert not impl_context_dir.exists()


def test_remove_impl_context_not_exists(tmp_path: Path) -> None:
    """Test error when .erk/impl-context/ folder doesn't exist."""
    from erk_shared.impl_context import remove_impl_context

    with pytest.raises(FileNotFoundError, match=".erk/impl-context/ folder does not exist"):
        remove_impl_context(tmp_path)


def test_remove_impl_context_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo_root doesn't exist."""
    from erk_shared.impl_context import remove_impl_context

    nonexistent_path = tmp_path / "nonexistent"

    with pytest.raises(ValueError, match="Repository root does not exist"):
        remove_impl_context(nonexistent_path)


def test_impl_context_exists_true(tmp_path: Path) -> None:
    """Test impl_context_exists returns True when folder exists."""
    from erk_shared.impl_context import create_impl_context, impl_context_exists

    # Create .erk/impl-context/ folder
    create_impl_context(
        plan_content="# Test\n",
        plan_id="123",
        url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
        provider="github",
        objective_id=None,
    )

    assert impl_context_exists(tmp_path) is True


def test_impl_context_exists_false(tmp_path: Path) -> None:
    """Test impl_context_exists returns False when folder doesn't exist."""
    from erk_shared.impl_context import impl_context_exists

    assert impl_context_exists(tmp_path) is False


def test_impl_context_exists_repo_root_not_exists(tmp_path: Path) -> None:
    """Test impl_context_exists returns False when repo_root doesn't exist."""
    from erk_shared.impl_context import impl_context_exists

    nonexistent_path = tmp_path / "nonexistent"

    assert impl_context_exists(nonexistent_path) is False


def test_impl_context_plan_content_preservation(tmp_path: Path) -> None:
    """Test that plan content is preserved exactly as provided."""
    from erk_shared.impl_context import create_impl_context

    # Plan with special characters and formatting
    plan_content = """# Implementation Plan

## Overview
This plan contains **markdown** formatting and `code blocks`.

## Tasks

1. First task with `inline code`
2. Second task with special chars: $, &, *, ()

```python
def example():
    return "code block"
```

> Note: blockquote text
"""
    create_impl_context(
        plan_content=plan_content,
        plan_id="456",
        url="https://github.com/owner/repo/issues/456",
        repo_root=tmp_path,
        provider="github",
        objective_id=None,
    )

    plan_file = tmp_path / ".erk" / "impl-context" / "plan.md"
    saved_content = plan_file.read_text(encoding="utf-8")

    # Content should be preserved exactly
    assert saved_content == plan_content


def test_create_impl_context_with_objective_id(tmp_path: Path) -> None:
    """Test creating .erk/impl-context/ folder with objective_id included."""
    from erk_shared.impl_context import create_impl_context

    create_impl_context(
        plan_content="# Test Plan\n",
        plan_id="123",
        url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
        provider="github",
        objective_id=456,
    )

    ref_file = tmp_path / ".erk" / "impl-context" / "ref.json"
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))

    assert ref_data["plan_id"] == "123"
    assert ref_data["objective_id"] == 456


def test_create_impl_context_with_draft_pr_provider(tmp_path: Path) -> None:
    """Test creating .erk/impl-context/ folder with github-draft-pr provider."""
    from erk_shared.impl_context import create_impl_context

    create_impl_context(
        plan_content="# Test Plan\n",
        plan_id="789",
        url="https://github.com/owner/repo/pull/789",
        repo_root=tmp_path,
        provider="github-draft-pr",
        objective_id=None,
    )

    ref_file = tmp_path / ".erk" / "impl-context" / "ref.json"
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))

    assert ref_data["provider"] == "github-draft-pr"
    assert ref_data["plan_id"] == "789"
    assert ref_data["url"] == "https://github.com/owner/repo/pull/789"


def test_create_impl_context_no_readme(tmp_path: Path) -> None:
    """Test that .erk/impl-context/ does NOT contain README.md."""
    from erk_shared.impl_context import create_impl_context

    create_impl_context(
        plan_content="# Test Plan\n",
        plan_id="123",
        url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
        provider="github",
        objective_id=None,
    )

    readme_file = tmp_path / ".erk" / "impl-context" / "README.md"
    assert not readme_file.exists()
