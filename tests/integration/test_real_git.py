"""Integration tests for git operations.

These tests verify that RealGit correctly handles git operations with real git repositories.
Integration tests use actual git subprocess calls to validate the abstractions.
"""

import subprocess
from pathlib import Path

import pytest

from erk_shared.git.real import RealGit
from tests.integration.conftest import (
    GitSetup,
    GitWithDetached,
    GitWithExistingBranch,
    GitWithWorktrees,
    init_git_repo,
)


def test_list_worktrees_single_repo(git_ops: GitSetup) -> None:
    """Test listing worktrees returns only main repository when no worktrees exist."""
    worktrees = git_ops.git.list_worktrees(git_ops.repo)

    assert len(worktrees) == 1
    assert worktrees[0].path == git_ops.repo
    assert worktrees[0].branch == "main"


def test_list_worktrees_multiple(git_ops_with_worktrees: GitWithWorktrees) -> None:
    """Test listing worktrees with multiple worktrees."""
    worktrees = git_ops_with_worktrees.git.list_worktrees(git_ops_with_worktrees.repo)

    assert len(worktrees) == 3

    # Find each worktree
    main_wt = next(wt for wt in worktrees if wt.branch == "main")
    feat1_wt = next(wt for wt in worktrees if wt.branch == "feature-1")
    feat2_wt = next(wt for wt in worktrees if wt.branch == "feature-2")

    assert main_wt.path == git_ops_with_worktrees.repo
    assert feat1_wt.path == git_ops_with_worktrees.worktrees[0]
    assert feat2_wt.path == git_ops_with_worktrees.worktrees[1]


def test_list_worktrees_detached_head(git_ops_with_detached: GitWithDetached) -> None:
    """Test listing worktrees includes detached HEAD worktree with None branch."""
    worktrees = git_ops_with_detached.git.list_worktrees(git_ops_with_detached.repo)

    assert len(worktrees) == 2
    detached_wt = next(wt for wt in worktrees if wt.path == git_ops_with_detached.detached_wt)
    assert detached_wt.branch is None


def test_get_current_branch_normal(git_ops: GitSetup) -> None:
    """Test getting current branch in normal checkout."""
    branch = git_ops.git.get_current_branch(git_ops.repo)

    assert branch == "main"


def test_get_current_branch_after_checkout(git_ops: GitSetup) -> None:
    """Test getting current branch after checking out a different branch."""
    # Create and checkout new branch
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=git_ops.repo, check=True)

    branch = git_ops.git.get_current_branch(git_ops.repo)

    assert branch == "feature"


def test_get_current_branch_detached_head(git_ops: GitSetup) -> None:
    """Test getting current branch in detached HEAD state returns None."""
    # Get commit hash and checkout in detached state
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_ops.repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_hash = result.stdout.strip()
    subprocess.run(["git", "checkout", commit_hash], cwd=git_ops.repo, check=True)

    branch = git_ops.git.get_current_branch(git_ops.repo)

    assert branch is None


def test_get_current_branch_non_git_directory(git_ops: GitSetup, tmp_path: Path) -> None:
    """Test getting current branch in non-git directory returns None."""
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()

    branch = git_ops.git.get_current_branch(non_git)

    assert branch is None


def test_detect_trunk_branch_main(git_ops: GitSetup) -> None:
    """Test detecting trunk branch when it's main."""
    trunk_branch = git_ops.git.detect_trunk_branch(git_ops.repo)

    assert trunk_branch == "main"


def test_detect_trunk_branch_master(
    tmp_path: Path,
) -> None:
    """Test detecting trunk branch when it's master using real git."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    # Create real repo with master branch
    init_git_repo(repo, "master")
    git_ops = RealGit()

    trunk_branch = git_ops.detect_trunk_branch(repo)

    assert trunk_branch == "master"


def test_detect_trunk_branch_with_remote_head(
    tmp_path: Path,
) -> None:
    """Test detecting trunk branch using remote HEAD with real git."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Set up remote HEAD manually
    subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
        cwd=repo,
        check=True,
    )

    git_ops = RealGit()

    trunk_branch = git_ops.detect_trunk_branch(repo)

    assert trunk_branch == "main"


def test_detect_trunk_branch_neither_exists(
    tmp_path: Path,
) -> None:
    """Test trunk branch detection returns 'main' when neither main nor master exist."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "trunk")

    # Delete the trunk branch we just created (keep the commit)
    subprocess.run(["git", "checkout", "--detach"], cwd=repo, check=True)
    subprocess.run(["git", "branch", "-D", "trunk"], cwd=repo, check=True)

    git_ops = RealGit()

    # New behavior: returns "main" as final fallback
    trunk_branch = git_ops.detect_trunk_branch(repo)
    assert trunk_branch == "main"


def test_validate_trunk_branch_exists(tmp_path: Path) -> None:
    """Test validate_trunk_branch succeeds when branch exists."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    git_ops = RealGit()
    result = git_ops.validate_trunk_branch(repo, "main")

    assert result == "main"


def test_validate_trunk_branch_not_exists(tmp_path: Path) -> None:
    """Test validate_trunk_branch raises RuntimeError when branch doesn't exist."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    git_ops = RealGit()

    with pytest.raises(RuntimeError, match="does not exist in repository"):
        git_ops.validate_trunk_branch(repo, "nonexistent")


def test_get_git_common_dir_from_main_repo(git_ops: GitSetup) -> None:
    """Test getting git common dir from main repository."""
    git_dir = git_ops.git.get_git_common_dir(git_ops.repo)

    assert git_dir is not None
    assert git_dir == git_ops.repo / ".git"


def test_get_git_common_dir_from_worktree(git_ops_with_worktrees: GitWithWorktrees) -> None:
    """Test getting git common dir from worktree returns shared .git directory."""
    wt = git_ops_with_worktrees.worktrees[0]

    git_dir = git_ops_with_worktrees.git.get_git_common_dir(wt)

    assert git_dir is not None
    assert git_dir == git_ops_with_worktrees.repo / ".git"


def test_get_git_common_dir_non_git_directory(git_ops: GitSetup, tmp_path: Path) -> None:
    """Test getting git common dir in non-git directory returns None."""
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()

    git_dir = git_ops.git.get_git_common_dir(non_git)

    assert git_dir is None


def test_add_worktree_with_existing_branch(
    git_ops_with_existing_branch: GitWithExistingBranch,
) -> None:
    """Test adding worktree with existing branch."""
    # Create the feature branch
    subprocess.run(
        ["git", "branch", "feature"],
        cwd=git_ops_with_existing_branch.repo,
        check=True,
    )

    git_ops_with_existing_branch.git.add_worktree(
        git_ops_with_existing_branch.repo,
        git_ops_with_existing_branch.wt_path,
        branch="feature",
        ref=None,
        create_branch=False,
    )

    assert git_ops_with_existing_branch.wt_path.exists()

    # Verify branch is checked out
    branch = git_ops_with_existing_branch.git.get_current_branch(
        git_ops_with_existing_branch.wt_path
    )
    assert branch == "feature"


def test_add_worktree_create_new_branch(
    git_ops_with_existing_branch: GitWithExistingBranch,
) -> None:
    """Test adding worktree with new branch creation."""
    git_ops_with_existing_branch.git.add_worktree(
        git_ops_with_existing_branch.repo,
        git_ops_with_existing_branch.wt_path,
        branch="new-feature",
        ref=None,
        create_branch=True,
    )

    assert git_ops_with_existing_branch.wt_path.exists()

    # Verify new branch is checked out
    branch = git_ops_with_existing_branch.git.get_current_branch(
        git_ops_with_existing_branch.wt_path
    )
    assert branch == "new-feature"


def test_add_worktree_from_specific_ref(
    tmp_path: Path,
) -> None:
    """Test adding worktree from specific ref using real git."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()
    wt = tmp_path / "wt"

    init_git_repo(repo, "main")

    # Create another commit on main
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=repo, check=True)

    # Create branch at main
    subprocess.run(["git", "branch", "old-main", "HEAD~1"], cwd=repo, check=True)

    git_ops = RealGit()

    git_ops.add_worktree(repo, wt, branch="test-branch", ref="old-main", create_branch=True)

    assert wt.exists()


def test_add_worktree_detached(git_ops_with_existing_branch: GitWithExistingBranch) -> None:
    """Test adding detached worktree."""
    git_ops_with_existing_branch.git.add_worktree(
        git_ops_with_existing_branch.repo,
        git_ops_with_existing_branch.wt_path,
        branch=None,
        ref="HEAD",
        create_branch=False,
    )

    assert git_ops_with_existing_branch.wt_path.exists()

    # Verify it's in detached HEAD state
    branch = git_ops_with_existing_branch.git.get_current_branch(
        git_ops_with_existing_branch.wt_path
    )
    assert branch is None


def test_move_worktree(git_ops_with_worktrees: GitWithWorktrees) -> None:
    """Test moving worktree to new location."""
    old_path = git_ops_with_worktrees.worktrees[0]

    new_base_path = git_ops_with_worktrees.repo.parent / "new"
    new_base_path.mkdir(parents=True, exist_ok=True)

    git_ops_with_worktrees.git.move_worktree(git_ops_with_worktrees.repo, old_path, new_base_path)

    # Verify old path doesn't exist
    assert not old_path.exists()

    # Verify git still tracks it correctly
    worktrees = git_ops_with_worktrees.git.list_worktrees(git_ops_with_worktrees.repo)
    moved_wt = next(wt for wt in worktrees if wt.branch == "feature-1")
    # Git moves to new/wt1 (subdirectory)
    assert moved_wt.path in [new_base_path, new_base_path / old_path.name]


def test_remove_worktree(git_ops_with_worktrees: GitWithWorktrees) -> None:
    """Test removing worktree."""
    wt = git_ops_with_worktrees.worktrees[0]

    # Ensure worktree directory exists for both implementations
    if not wt.exists():
        wt.mkdir(parents=True, exist_ok=True)

    git_ops_with_worktrees.git.remove_worktree(git_ops_with_worktrees.repo, wt, force=False)

    # Verify it's removed
    worktrees = git_ops_with_worktrees.git.list_worktrees(git_ops_with_worktrees.repo)
    assert len(worktrees) == 2  # Only main and feature-2 remain
    assert worktrees[0].branch == "main"


def test_remove_worktree_with_force(git_ops_with_worktrees: GitWithWorktrees) -> None:
    """Test removing worktree with force flag."""
    wt = git_ops_with_worktrees.worktrees[0]

    # Ensure worktree directory exists
    if not wt.exists():
        wt.mkdir(parents=True, exist_ok=True)

    # Add uncommitted changes
    (wt / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    # Remove with force
    git_ops_with_worktrees.git.remove_worktree(git_ops_with_worktrees.repo, wt, force=True)

    # Verify it's removed
    worktrees = git_ops_with_worktrees.git.list_worktrees(git_ops_with_worktrees.repo)
    assert len(worktrees) == 2  # Only main and feature-2 remain
    assert worktrees[0].branch == "main"


def test_checkout_branch(
    tmp_path: Path,
) -> None:
    """Test checking out a branch using real git."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create a new branch
    subprocess.run(["git", "branch", "feature"], cwd=repo, check=True)

    git_ops = RealGit()

    # Checkout the branch
    git_ops.checkout_branch(repo, "feature")

    # Verify branch is checked out
    branch = git_ops.get_current_branch(repo)
    assert branch == "feature"


def test_checkout_branch_in_worktree(
    tmp_path: Path,
) -> None:
    """Test checking out a branch within a worktree using real git."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()
    wt = tmp_path / "wt"

    init_git_repo(repo, "main")

    # Create worktree with feature-1
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-1", str(wt)],
        cwd=repo,
        check=True,
    )

    # Create another branch from the worktree
    subprocess.run(["git", "branch", "feature-2"], cwd=wt, check=True)

    git_ops = RealGit()

    # Checkout feature-2 in the worktree
    git_ops.checkout_branch(wt, "feature-2")

    # Verify branch is checked out
    branch = git_ops.get_current_branch(wt)
    assert branch == "feature-2"


def test_remove_worktree_called_from_worktree_path(
    tmp_path: Path,
) -> None:
    """Test that remove_worktree works when repo_root IS the worktree being deleted.

    This is a regression test for issue #2345:
    When remove_worktree is called with repo_root pointing to the worktree path itself,
    the prune step would fail because the cwd no longer exists after git worktree remove.

    The fix is to resolve the main git directory BEFORE deleting the worktree,
    and use that path for the prune command.
    """
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    # Setup: Create main repo and a worktree
    repo = tmp_path / "repo"
    repo.mkdir()
    wt = tmp_path / "wt"

    init_git_repo(repo, "main")

    # Create a worktree
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-1", str(wt)],
        cwd=repo,
        check=True,
    )

    # Verify worktree exists
    assert wt.exists()

    git_ops = RealGit()

    # Act: Remove worktree using the WORKTREE PATH as repo_root
    # This simulates the case where we're inside the worktree and calling remove
    # The key is that after git worktree remove runs, the wt path no longer exists
    # so git worktree prune would fail if it tried to use wt as cwd
    git_ops.remove_worktree(wt, wt, force=True)

    # Assert: Worktree was removed successfully
    # This would have raised RuntimeError("Command not found...") before the fix
    assert not wt.exists()

    # Verify git still tracks the main repo correctly
    worktrees = git_ops.list_worktrees(repo)
    assert len(worktrees) == 1
    assert worktrees[0].path == repo
    assert worktrees[0].branch == "main"


def test_find_main_git_dir_from_worktree(
    tmp_path: Path,
) -> None:
    """Test _find_main_git_dir correctly resolves main repo from a worktree."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    # Setup: Create main repo and a worktree
    repo = tmp_path / "repo"
    repo.mkdir()
    wt = tmp_path / "wt"

    init_git_repo(repo, "main")

    # Create a worktree
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature", str(wt)],
        cwd=repo,
        check=True,
    )

    git_ops = RealGit()

    # Act: Find main git dir from both locations
    main_from_repo = git_ops._find_main_git_dir(repo)
    main_from_wt = git_ops._find_main_git_dir(wt)

    # Assert: Both should resolve to the main repo root
    assert main_from_repo == repo
    assert main_from_wt == repo


def test_find_main_git_dir_from_main_repo(
    tmp_path: Path,
) -> None:
    """Test _find_main_git_dir returns repo_root when called on main repo."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    git_ops = RealGit()

    # Act
    main_dir = git_ops._find_main_git_dir(repo)

    # Assert
    assert main_dir == repo


def test_get_commit_messages_since_returns_messages(tmp_path: Path) -> None:
    """Test get_commit_messages_since returns full commit messages."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create feature branch with multiple commits
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)

    # First commit
    (repo / "file1.txt").write_text("content1\n", encoding="utf-8")
    subprocess.run(["git", "add", "file1.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add file1\n\nThis is the body."],
        cwd=repo,
        check=True,
    )

    # Second commit
    (repo / "file2.txt").write_text("content2\n", encoding="utf-8")
    subprocess.run(["git", "add", "file2.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file2"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act
    messages = git_ops.get_commit_messages_since(repo, "main")

    # Assert: Should have 2 messages in chronological order
    assert len(messages) == 2
    assert "Add file1" in messages[0]
    assert "This is the body" in messages[0]  # Full message with body
    assert "Add file2" in messages[1]


def test_get_commit_messages_since_returns_empty_for_no_commits(tmp_path: Path) -> None:
    """Test get_commit_messages_since returns empty list when no commits ahead."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    git_ops = RealGit()

    # Act: main..main has no commits
    messages = git_ops.get_commit_messages_since(repo, "main")

    # Assert
    assert messages == []


def test_get_commit_messages_since_returns_empty_for_invalid_branch(tmp_path: Path) -> None:
    """Test get_commit_messages_since returns empty list for nonexistent branch."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    git_ops = RealGit()

    # Act: nonexistent base branch
    messages = git_ops.get_commit_messages_since(repo, "nonexistent")

    # Assert: Returns empty list (graceful degradation)
    assert messages == []


def test_has_uncommitted_changes_clean(tmp_path: Path) -> None:
    """Test has_uncommitted_changes returns False when working directory is clean."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    git_ops = RealGit()

    # Act: Check for uncommitted changes in clean repo
    has_changes = git_ops.has_uncommitted_changes(repo)

    # Assert: Should be clean after init
    assert has_changes is False


def test_has_uncommitted_changes_with_modifications(tmp_path: Path) -> None:
    """Test has_uncommitted_changes returns True when files are modified."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create a new untracked file
    (repo / "new_file.txt").write_text("new content\n", encoding="utf-8")

    git_ops = RealGit()

    # Act
    has_changes = git_ops.has_uncommitted_changes(repo)

    # Assert
    assert has_changes is True


def test_add_all_stages_files(tmp_path: Path) -> None:
    """Test add_all stages all files in the repository."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create new files
    (repo / "file1.txt").write_text("content1\n", encoding="utf-8")
    (repo / "file2.txt").write_text("content2\n", encoding="utf-8")

    git_ops = RealGit()

    # Act
    git_ops.add_all(repo)

    # Assert: Verify files are staged
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    # Staged new files show as "A " (added to index)
    assert "A  file1.txt" in result.stdout
    assert "A  file2.txt" in result.stdout


def test_commit_creates_commit(tmp_path: Path) -> None:
    """Test commit creates a commit with the given message."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create and stage a file
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act
    git_ops.commit(repo, "Test commit message")

    # Assert: Verify commit was created
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Test commit message" in result.stdout


def test_amend_commit_modifies_commit(tmp_path: Path) -> None:
    """Test amend_commit modifies the last commit message."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Modify a file and stage it
    (repo / "README.md").write_text("modified content\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act
    git_ops.amend_commit(repo, "Amended commit message")

    # Assert: Verify commit was amended
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Amended commit message" in result.stdout


def test_amend_commit_with_backticks(tmp_path: Path) -> None:
    """Test amend_commit handles backticks in commit messages correctly.

    This tests edge case behavior around shell quoting that could cause issues.
    """
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Modify a file and stage it
    (repo / "README.md").write_text("modified content\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act: Amend with backticks in message
    message_with_backticks = "feat: add `some_function()` implementation"
    git_ops.amend_commit(repo, message_with_backticks)

    # Assert: Verify message was set correctly
    result = subprocess.run(
        ["git", "log", "-1", "--format=%B"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert message_with_backticks in result.stdout


def test_count_commits_ahead(tmp_path: Path) -> None:
    """Test count_commits_ahead counts commits since base branch."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create feature branch with multiple commits
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)

    for i in range(3):
        (repo / f"file{i}.txt").write_text(f"content{i}\n", encoding="utf-8")
        subprocess.run(["git", "add", f"file{i}.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", f"Commit {i}"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act
    count = git_ops.count_commits_ahead(repo, "main")

    # Assert
    assert count == 3


def test_check_merge_conflicts_detects_conflicts(tmp_path: Path) -> None:
    """Test check_merge_conflicts detects conflicting changes between branches."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create a file on main
    (repo / "file.txt").write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=repo, check=True)

    # Create feature branch and modify same lines
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)
    (repo / "file.txt").write_text("line 1 CHANGED\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "Change on feature"], cwd=repo, check=True)

    # Go back to main and make conflicting change
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)
    (repo / "file.txt").write_text("line 1 DIFFERENT\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "Change on main"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act
    has_conflicts = git_ops.check_merge_conflicts(repo, "main", "feature")

    # Assert
    assert has_conflicts is True


def test_check_merge_conflicts_no_conflicts(tmp_path: Path) -> None:
    """Test check_merge_conflicts returns False when branches can merge cleanly."""
    from erk_shared.git.real import RealGit
    from tests.integration.conftest import init_git_repo

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create feature branch with non-conflicting changes
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)
    (repo / "new_file.txt").write_text("new content\n", encoding="utf-8")
    subprocess.run(["git", "add", "new_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add new file"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act
    has_conflicts = git_ops.check_merge_conflicts(repo, "main", "feature")

    # Assert
    assert has_conflicts is False


def test_rebase_onto_success(tmp_path: Path) -> None:
    """Test rebase_onto successfully rebases a branch onto target ref."""
    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create a base branch with a commit
    subprocess.run(["git", "checkout", "-b", "base"], cwd=repo, check=True)
    (repo / "base_file.txt").write_text("base content\n", encoding="utf-8")
    subprocess.run(["git", "add", "base_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add base file"], cwd=repo, check=True)

    # Go back to main and create feature branch
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)
    (repo / "feature_file.txt").write_text("feature content\n", encoding="utf-8")
    subprocess.run(["git", "add", "feature_file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add feature file"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act: Rebase feature onto base
    result = git_ops.rebase_onto(repo, "base")

    # Assert
    assert result.success is True
    assert result.conflict_files == ()

    # Verify feature branch now has base_file.txt (from base branch)
    assert (repo / "base_file.txt").exists()
    # Verify feature_file.txt still exists
    assert (repo / "feature_file.txt").exists()


def test_rebase_onto_with_conflicts(tmp_path: Path) -> None:
    """Test rebase_onto detects conflicts and returns them."""
    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create a file on main
    (repo / "file.txt").write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=repo, check=True)

    # Create base branch with conflicting changes
    subprocess.run(["git", "checkout", "-b", "base"], cwd=repo, check=True)
    (repo / "file.txt").write_text("line 1 BASE\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "Change on base"], cwd=repo, check=True)

    # Go back to main and create feature with conflicting changes
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)
    (repo / "file.txt").write_text("line 1 FEATURE\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "Change on feature"], cwd=repo, check=True)

    git_ops = RealGit()

    # Act: Rebase feature onto base (should conflict)
    result = git_ops.rebase_onto(repo, "base")

    # Assert
    assert result.success is False
    assert "file.txt" in result.conflict_files

    # Clean up: abort the rebase
    git_ops.rebase_abort(repo)


def test_rebase_abort_cancels_rebase(tmp_path: Path) -> None:
    """Test rebase_abort cancels an in-progress rebase."""
    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create conflicting setup (same as test_rebase_onto_with_conflicts)
    (repo / "file.txt").write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=repo, check=True)

    subprocess.run(["git", "checkout", "-b", "base"], cwd=repo, check=True)
    (repo / "file.txt").write_text("line 1 BASE\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "Change on base"], cwd=repo, check=True)

    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo, check=True)
    (repo / "file.txt").write_text("line 1 FEATURE\nline 2\nline 3\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "Change on feature"], cwd=repo, check=True)

    git_ops = RealGit()

    # Start a rebase that will conflict
    result = git_ops.rebase_onto(repo, "base")
    assert result.success is False

    # Verify rebase is in progress
    assert git_ops.is_rebase_in_progress(repo) is True

    # Act: Abort the rebase
    git_ops.rebase_abort(repo)

    # Assert: Rebase is no longer in progress
    assert git_ops.is_rebase_in_progress(repo) is False

    # Verify we're back on feature branch with original content
    branch = git_ops.get_current_branch(repo)
    assert branch == "feature"
    assert "FEATURE" in (repo / "file.txt").read_text()


def test_pull_rebase_integrates_remote_commits(tmp_path: Path) -> None:
    """Test pull_rebase integrates remote commits via rebase."""
    # Setup: Create a "remote" repo and a "local" clone
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    local_repo = tmp_path / "local"

    init_git_repo(remote_repo, "main")

    # Clone the remote
    subprocess.run(
        ["git", "clone", str(remote_repo), str(local_repo)],
        check=True,
        capture_output=True,
    )

    # Configure git identity in cloned repo (needed for CI)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=local_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=local_repo, check=True)

    # Create a local commit
    (local_repo / "local_file.txt").write_text("local content\n", encoding="utf-8")
    subprocess.run(["git", "add", "local_file.txt"], cwd=local_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add local file"], cwd=local_repo, check=True)

    # Create a remote commit (simulating CI adding a commit)
    (remote_repo / "remote_file.txt").write_text("remote content\n", encoding="utf-8")
    subprocess.run(["git", "add", "remote_file.txt"], cwd=remote_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add remote file"], cwd=remote_repo, check=True)

    git_ops = RealGit()

    # Act: Pull with rebase
    git_ops.pull_rebase(local_repo, "origin", "main")

    # Assert: Local should now have both files
    assert (local_repo / "local_file.txt").exists()
    assert (local_repo / "remote_file.txt").exists()

    # Verify the local commit was rebased on top of remote
    result = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        cwd=local_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    # Local commit should be on top (most recent)
    assert "Add local file" in result.stdout.split("\n")[0]
    # Remote commit should be below
    assert "Add remote file" in result.stdout


def test_get_behind_commit_authors_no_upstream(tmp_path: Path) -> None:
    """Test get_behind_commit_authors returns empty list when no upstream tracking branch."""
    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    git_ops = RealGit()

    # Act: Branch has no upstream (local-only repo)
    authors = git_ops.get_behind_commit_authors(repo, "main")

    # Assert: No upstream, so empty list
    assert authors == []


def test_get_behind_commit_authors_up_to_date(tmp_path: Path) -> None:
    """Test get_behind_commit_authors returns empty list when local is up to date with remote."""
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    local_repo = tmp_path / "local"

    init_git_repo(remote_repo, "main")

    # Clone the remote
    subprocess.run(
        ["git", "clone", str(remote_repo), str(local_repo)],
        check=True,
        capture_output=True,
    )

    git_ops = RealGit()

    # Act: Local is at same commit as remote
    authors = git_ops.get_behind_commit_authors(local_repo, "main")

    # Assert: Up to date, so empty list
    assert authors == []


def test_get_behind_commit_authors_returns_authors_from_remote(tmp_path: Path) -> None:
    """Test get_behind_commit_authors returns author names for commits on remote but not locally."""
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    local_repo = tmp_path / "local"

    init_git_repo(remote_repo, "main")

    # Clone the remote
    subprocess.run(
        ["git", "clone", str(remote_repo), str(local_repo)],
        check=True,
        capture_output=True,
    )

    # Add commits to remote (simulating CI or other users)
    (remote_repo / "file1.txt").write_text("content1\n", encoding="utf-8")
    subprocess.run(["git", "add", "file1.txt"], cwd=remote_repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Alice",
            "-c",
            "user.email=alice@example.com",
            "commit",
            "-m",
            "Add file1",
        ],
        cwd=remote_repo,
        check=True,
    )

    # Fetch but don't merge/pull
    subprocess.run(["git", "fetch", "origin"], cwd=local_repo, check=True)

    git_ops = RealGit()

    # Act
    authors = git_ops.get_behind_commit_authors(local_repo, "main")

    # Assert: Should contain Alice's commit
    assert len(authors) == 1
    assert authors[0] == "Alice"


def test_get_behind_commit_authors_multiple_authors(tmp_path: Path) -> None:
    """Test get_behind_commit_authors handles multiple authors correctly."""
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    local_repo = tmp_path / "local"

    init_git_repo(remote_repo, "main")

    # Clone the remote
    subprocess.run(
        ["git", "clone", str(remote_repo), str(local_repo)],
        check=True,
        capture_output=True,
    )

    # Add commits from multiple authors to remote
    (remote_repo / "file1.txt").write_text("content1\n", encoding="utf-8")
    subprocess.run(["git", "add", "file1.txt"], cwd=remote_repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Alice",
            "-c",
            "user.email=alice@example.com",
            "commit",
            "-m",
            "Add file1",
        ],
        cwd=remote_repo,
        check=True,
    )

    (remote_repo / "file2.txt").write_text("content2\n", encoding="utf-8")
    subprocess.run(["git", "add", "file2.txt"], cwd=remote_repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Bob",
            "-c",
            "user.email=bob@example.com",
            "commit",
            "-m",
            "Add file2",
        ],
        cwd=remote_repo,
        check=True,
    )

    # Fetch but don't merge/pull
    subprocess.run(["git", "fetch", "origin"], cwd=local_repo, check=True)

    git_ops = RealGit()

    # Act
    authors = git_ops.get_behind_commit_authors(local_repo, "main")

    # Assert: Should contain both authors (most recent first from git log)
    assert len(authors) == 2
    assert "Alice" in authors
    assert "Bob" in authors


def test_get_behind_commit_authors_with_bot_author(tmp_path: Path) -> None:
    """Test get_behind_commit_authors handles bot authors like github-actions[bot]."""
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    local_repo = tmp_path / "local"

    init_git_repo(remote_repo, "main")

    # Clone the remote
    subprocess.run(
        ["git", "clone", str(remote_repo), str(local_repo)],
        check=True,
        capture_output=True,
    )

    # Add commit from a bot author (simulating CI autofix)
    (remote_repo / "autofix.txt").write_text("autofix content\n", encoding="utf-8")
    subprocess.run(["git", "add", "autofix.txt"], cwd=remote_repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=github-actions[bot]",
            "-c",
            "user.email=github-actions[bot]@users.noreply.github.com",
            "commit",
            "-m",
            "Autofix: format code",
        ],
        cwd=remote_repo,
        check=True,
    )

    # Fetch but don't merge/pull
    subprocess.run(["git", "fetch", "origin"], cwd=local_repo, check=True)

    git_ops = RealGit()

    # Act
    authors = git_ops.get_behind_commit_authors(local_repo, "main")

    # Assert: Should contain the bot author name
    assert len(authors) == 1
    assert authors[0] == "github-actions[bot]"
