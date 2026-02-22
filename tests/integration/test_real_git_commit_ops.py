"""Integration tests for RealGitCommitOps.commit_files_to_branch().

Tests verify that commit_files_to_branch correctly creates commits on a branch
using git plumbing commands without modifying the working tree or HEAD.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from erk_shared.gateway.git.commit_ops.real import RealGitCommitOps
from erk_shared.gateway.time.real import RealTime
from tests.integration.conftest import init_git_repo


def _make_commit_ops() -> RealGitCommitOps:
    return RealGitCommitOps(time=RealTime())


def test_commit_files_to_branch_creates_commit_on_target_branch(tmp_path: Path) -> None:
    """Test that commit_files_to_branch creates a commit on the target branch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    commit_ops = _make_commit_ops()

    # Act: Commit a file to main using plumbing
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={"plan.md": "# My Plan\n\nStep 1: Do the thing.\n"},
        message="Add plan file",
    )

    # Assert: The commit exists on main
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "Add plan file"

    # Assert: The file content is accessible via git show
    result = subprocess.run(
        ["git", "show", "main:plan.md"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "# My Plan\n\nStep 1: Do the thing.\n"


def test_commit_files_to_branch_does_not_modify_working_tree(tmp_path: Path) -> None:
    """Test that commit_files_to_branch does not modify the working tree or HEAD."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a different branch and switch to it
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)

    commit_ops = _make_commit_ops()

    # Act: Commit to main while on feature branch
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={"new-file.txt": "content\n"},
        message="Add file to main",
    )

    # Assert: HEAD is still on feature branch
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert current_branch == "feature"

    # Assert: Working tree has no new files
    assert not (repo / "new-file.txt").exists()

    # Assert: The file exists on main but not in the working tree
    result = subprocess.run(
        ["git", "show", "main:new-file.txt"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "content\n"


def test_commit_files_to_branch_with_multiple_files(tmp_path: Path) -> None:
    """Test that commit_files_to_branch handles multiple files in a single commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    commit_ops = _make_commit_ops()

    # Act: Commit multiple files
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={
            "file1.txt": "content one\n",
            "file2.txt": "content two\n",
            "subdir/file3.txt": "content three\n",
        },
        message="Add multiple files",
    )

    # Assert: All files exist on the branch
    for path, expected_content in [
        ("file1.txt", "content one\n"),
        ("file2.txt", "content two\n"),
        ("subdir/file3.txt", "content three\n"),
    ]:
        result = subprocess.run(
            ["git", "show", f"main:{path}"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout == expected_content, f"Content mismatch for {path}"


def test_commit_files_to_branch_preserves_existing_files(tmp_path: Path) -> None:
    """Test that commit_files_to_branch preserves existing files on the branch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    commit_ops = _make_commit_ops()

    # Act: Add a new file (README.md already exists from init_git_repo)
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={"new-file.txt": "new content\n"},
        message="Add new file",
    )

    # Assert: Original README.md still exists
    result = subprocess.run(
        ["git", "show", "main:README.md"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "# Test Repository\n"

    # Assert: New file also exists
    result = subprocess.run(
        ["git", "show", "main:new-file.txt"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "new content\n"


def test_commit_files_to_branch_updates_existing_file(tmp_path: Path) -> None:
    """Test that commit_files_to_branch can overwrite an existing file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    commit_ops = _make_commit_ops()

    # Act: Overwrite README.md
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={"README.md": "# Updated Repository\n\nNew description.\n"},
        message="Update README",
    )

    # Assert: README.md has new content
    result = subprocess.run(
        ["git", "show", "main:README.md"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "# Updated Repository\n\nNew description.\n"


def test_commit_files_to_branch_does_not_affect_real_index(tmp_path: Path) -> None:
    """Test that commit_files_to_branch uses a temp index and does not pollute the real one."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Switch to a feature branch so committing to main won't change HEAD
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)

    # Stage a file in the real index
    (repo / "staged.txt").write_text("staged content\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=repo, check=True)

    commit_ops = _make_commit_ops()

    # Act: Commit to main via plumbing while on feature branch
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={"plumbing-file.txt": "plumbing content\n"},
        message="Plumbing commit",
    )

    # Assert: The real index still has staged.txt
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "A  staged.txt" in result.stdout

    # Assert: The real index does NOT have plumbing-file.txt
    assert "plumbing-file.txt" not in result.stdout


def test_commit_files_to_branch_cleans_up_temp_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the temporary index file is cleaned up after the operation."""
    import tempfile

    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Use test-specific temp directory to avoid interference from parallel xdist workers
    test_temp_dir = tmp_path / "temp"
    test_temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(test_temp_dir))

    commit_ops = _make_commit_ops()

    # Act
    commit_ops.commit_files_to_branch(
        repo,
        branch="main",
        files={"file.txt": "content\n"},
        message="Test commit",
    )

    # Assert: No erk-plan-*.idx files remain in our isolated temp dir
    remaining = list(test_temp_dir.glob("erk-plan-*.idx"))
    assert remaining == [], f"Temp index files not cleaned up: {remaining}"
