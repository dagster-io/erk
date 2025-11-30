"""Tests for worker_impl_folder utilities.

Layer 3: Pure unit tests (zero dependencies).

These tests verify the worker_impl_folder module functions work correctly with
basic filesystem operations. No fakes or mocks needed.
"""

import json
from pathlib import Path

import pytest


def test_create_worker_impl_folder_success(tmp_path: Path) -> None:
    """Test creating .worker-impl/ folder with all required files."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder

    plan_content = "# Test Plan\n\n1. First step\n2. Second step"
    issue_number = 123
    issue_url = "https://github.com/owner/repo/issues/123"

    worker_impl_folder = create_worker_impl_folder(
        plan_content=plan_content,
        issue_number=issue_number,
        issue_url=issue_url,
        repo_root=tmp_path,
    )

    # Verify folder was created
    assert worker_impl_folder == tmp_path / ".worker-impl"
    assert worker_impl_folder.exists()
    assert worker_impl_folder.is_dir()

    # Verify plan.md exists with correct content
    plan_file = worker_impl_folder / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_content

    # Verify issue.json exists with correct structure (canonical schema from impl_folder)
    issue_file = worker_impl_folder / "issue.json"
    assert issue_file.exists()
    issue_data = json.loads(issue_file.read_text(encoding="utf-8"))
    assert issue_data["issue_number"] == issue_number
    assert issue_data["issue_url"] == issue_url
    assert "created_at" in issue_data
    assert "synced_at" in issue_data

    # Verify progress.md exists with checkboxes
    progress_file = worker_impl_folder / "progress.md"
    assert progress_file.exists()
    progress_content = progress_file.read_text(encoding="utf-8")
    assert "---" in progress_content  # Front matter
    assert "completed_steps: 0" in progress_content
    assert "total_steps: 2" in progress_content
    assert "- [ ] 1. First step" in progress_content
    assert "- [ ] 2. Second step" in progress_content

    # Verify README.md exists
    readme_file = worker_impl_folder / "README.md"
    assert readme_file.exists()
    readme_content = readme_file.read_text(encoding="utf-8")
    assert "Worker Implementation Plan" in readme_content
    assert f"issue #{issue_number}" in readme_content
    assert issue_url in readme_content


def test_create_worker_impl_folder_already_exists(tmp_path: Path) -> None:
    """Test error when .worker-impl/ folder already exists."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder

    # Create .worker-impl/ folder first
    worker_impl_folder = tmp_path / ".worker-impl"
    worker_impl_folder.mkdir()

    # Attempt to create again should raise FileExistsError
    with pytest.raises(FileExistsError, match=".worker-impl/ folder already exists"):
        create_worker_impl_folder(
            plan_content="# Test",
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
            repo_root=tmp_path,
        )


def test_create_worker_impl_folder_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo_root doesn't exist."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder

    nonexistent_path = tmp_path / "nonexistent"

    with pytest.raises(ValueError, match="Repository root does not exist"):
        create_worker_impl_folder(
            plan_content="# Test",
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
            repo_root=nonexistent_path,
        )


def test_create_worker_impl_folder_repo_root_not_directory(tmp_path: Path) -> None:
    """Test error when repo_root is a file, not a directory."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder

    # Create a file, not a directory
    file_path = tmp_path / "file.txt"
    file_path.write_text("test", encoding="utf-8")

    with pytest.raises(ValueError, match="Repository root is not a directory"):
        create_worker_impl_folder(
            plan_content="# Test",
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
            repo_root=file_path,
        )


def test_remove_worker_impl_folder_success(tmp_path: Path) -> None:
    """Test removing .worker-impl/ folder."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder, remove_worker_impl_folder

    # Create .worker-impl/ folder first
    create_worker_impl_folder(
        plan_content="# Test\n\n1. Step one",
        issue_number=123,
        issue_url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
    )

    worker_impl_folder = tmp_path / ".worker-impl"
    assert worker_impl_folder.exists()

    # Remove it
    remove_worker_impl_folder(tmp_path)

    # Verify it's gone
    assert not worker_impl_folder.exists()


def test_remove_worker_impl_folder_not_exists(tmp_path: Path) -> None:
    """Test error when .worker-impl/ folder doesn't exist."""
    from erk_shared.worker_impl_folder import remove_worker_impl_folder

    with pytest.raises(FileNotFoundError, match=".worker-impl/ folder does not exist"):
        remove_worker_impl_folder(tmp_path)


def test_remove_worker_impl_folder_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo_root doesn't exist."""
    from erk_shared.worker_impl_folder import remove_worker_impl_folder

    nonexistent_path = tmp_path / "nonexistent"

    with pytest.raises(ValueError, match="Repository root does not exist"):
        remove_worker_impl_folder(nonexistent_path)


def test_worker_impl_folder_exists_true(tmp_path: Path) -> None:
    """Test worker_impl_folder_exists returns True when folder exists."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder, worker_impl_folder_exists

    # Create .worker-impl/ folder
    create_worker_impl_folder(
        plan_content="# Test\n\n1. Step one",
        issue_number=123,
        issue_url="https://github.com/owner/repo/issues/123",
        repo_root=tmp_path,
    )

    assert worker_impl_folder_exists(tmp_path) is True


def test_worker_impl_folder_exists_false(tmp_path: Path) -> None:
    """Test worker_impl_folder_exists returns False when folder doesn't exist."""
    from erk_shared.worker_impl_folder import worker_impl_folder_exists

    assert worker_impl_folder_exists(tmp_path) is False


def test_worker_impl_folder_exists_repo_root_not_exists(tmp_path: Path) -> None:
    """Test worker_impl_folder_exists returns False when repo_root doesn't exist."""
    from erk_shared.worker_impl_folder import worker_impl_folder_exists

    nonexistent_path = tmp_path / "nonexistent"

    assert worker_impl_folder_exists(nonexistent_path) is False


def test_worker_impl_folder_plan_content_preservation(tmp_path: Path) -> None:
    """Test that plan content is preserved exactly as provided."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder

    # Plan with special characters and formatting
    plan_content = """# Implementation Plan

## Overview
This plan contains **markdown** formatting and `code blocks`.

### Steps
1. First step with `inline code`
2. Second step with special chars: $, &, *, ()

```python
def example():
    return "code block"
```

> Note: blockquote text
"""

    create_worker_impl_folder(
        plan_content=plan_content,
        issue_number=456,
        issue_url="https://github.com/owner/repo/issues/456",
        repo_root=tmp_path,
    )

    plan_file = tmp_path / ".worker-impl" / "plan.md"
    saved_content = plan_file.read_text(encoding="utf-8")

    # Content should be preserved exactly
    assert saved_content == plan_content


def test_worker_impl_folder_progress_generation(tmp_path: Path) -> None:
    """Test progress.md generation from plan steps."""
    from erk_shared.worker_impl_folder import create_worker_impl_folder

    plan_content = """# Test Plan

1. First step
2. Second step
3. Third step
"""

    create_worker_impl_folder(
        plan_content=plan_content,
        issue_number=789,
        issue_url="https://github.com/owner/repo/issues/789",
        repo_root=tmp_path,
    )

    progress_file = tmp_path / ".worker-impl" / "progress.md"
    progress_content = progress_file.read_text(encoding="utf-8")

    # Verify front matter
    assert "---" in progress_content
    assert "completed_steps: 0" in progress_content
    assert "total_steps: 3" in progress_content

    # Verify all steps have checkboxes
    assert "- [ ] 1. First step" in progress_content
    assert "- [ ] 2. Second step" in progress_content
    assert "- [ ] 3. Third step" in progress_content
