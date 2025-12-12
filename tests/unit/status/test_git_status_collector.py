"""Unit tests for GitStatusCollector."""

from pathlib import Path

from erk.status.collectors.git import GitStatusCollector
from erk_shared.git.fake import FakeGit
from tests.fakes.context import create_test_context


def test_git_status_collector_clean_working_directory(tmp_path: Path) -> None:
    """Test GitStatusCollector with clean working directory."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "feature-branch"},
        file_statuses={worktree_path: ([], [], [])},  # No files
        ahead_behind={(worktree_path, "feature-branch"): (0, 0)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "abc1234",
                    "message": "Initial commit",
                    "author": "Test User",
                    "date": "1 hour ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "feature-branch"
    assert result.clean is True
    assert result.ahead == 0
    assert result.behind == 0
    assert len(result.staged_files) == 0
    assert len(result.modified_files) == 0
    assert len(result.untracked_files) == 0
    assert len(result.recent_commits) == 1
    assert result.recent_commits[0].sha == "abc1234"


def test_git_status_collector_with_modified_files(tmp_path: Path) -> None:
    """Test GitStatusCollector with modified files."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "feature-branch"},
        file_statuses={worktree_path: ([], ["src/main.py", "README.md"], [])},
        ahead_behind={(worktree_path, "feature-branch"): (2, 0)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "def5678",
                    "message": "Fix bug",
                    "author": "Developer",
                    "date": "2 hours ago",
                },
                {
                    "sha": "abc1234",
                    "message": "Add feature",
                    "author": "Developer",
                    "date": "3 hours ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "feature-branch"
    assert result.clean is False
    assert result.ahead == 2
    assert result.behind == 0
    assert len(result.staged_files) == 0
    assert len(result.modified_files) == 2
    assert "src/main.py" in result.modified_files
    assert "README.md" in result.modified_files
    assert len(result.untracked_files) == 0


def test_git_status_collector_with_added_files(tmp_path: Path) -> None:
    """Test GitStatusCollector with staged/added files."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "new-feature"},
        file_statuses={worktree_path: (["new_file.py", "config.json"], [], [])},
        ahead_behind={(worktree_path, "new-feature"): (1, 0)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "ghi9012",
                    "message": "Add new files",
                    "author": "Developer",
                    "date": "1 minute ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "new-feature"
    assert result.clean is False
    assert result.ahead == 1
    assert result.behind == 0
    assert len(result.staged_files) == 2
    assert "new_file.py" in result.staged_files
    assert "config.json" in result.staged_files
    assert len(result.modified_files) == 0
    assert len(result.untracked_files) == 0


def test_git_status_collector_with_deleted_files(tmp_path: Path) -> None:
    """Test GitStatusCollector with deleted files in staging."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    # Deleted files show up as staged changes
    git_ops = FakeGit(
        current_branches={worktree_path: "cleanup-branch"},
        file_statuses={worktree_path: (["old_file.py", "deprecated.txt"], [], [])},
        ahead_behind={(worktree_path, "cleanup-branch"): (1, 0)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "jkl3456",
                    "message": "Remove old files",
                    "author": "Cleaner",
                    "date": "5 minutes ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "cleanup-branch"
    assert result.clean is False
    assert len(result.staged_files) == 2
    assert "old_file.py" in result.staged_files
    assert "deprecated.txt" in result.staged_files


def test_git_status_collector_with_untracked_files(tmp_path: Path) -> None:
    """Test GitStatusCollector with untracked files."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "experimental"},
        file_statuses={worktree_path: ([], [], ["temp.txt", ".env", "notes.md"])},
        ahead_behind={(worktree_path, "experimental"): (0, 0)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "mno7890",
                    "message": "Experimental work",
                    "author": "Researcher",
                    "date": "1 day ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "experimental"
    assert result.clean is False
    assert len(result.staged_files) == 0
    assert len(result.modified_files) == 0
    assert len(result.untracked_files) == 3
    assert "temp.txt" in result.untracked_files
    assert ".env" in result.untracked_files
    assert "notes.md" in result.untracked_files


def test_git_status_collector_ahead_behind_tracking(tmp_path: Path) -> None:
    """Test GitStatusCollector with commits ahead and behind tracking branch."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "feature-diverged"},
        file_statuses={worktree_path: ([], [], [])},
        ahead_behind={(worktree_path, "feature-diverged"): (3, 5)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "pqr1234",
                    "message": "Local change 1",
                    "author": "Dev",
                    "date": "1 hour ago",
                },
                {
                    "sha": "stu5678",
                    "message": "Local change 2",
                    "author": "Dev",
                    "date": "2 hours ago",
                },
                {
                    "sha": "vwx9012",
                    "message": "Local change 3",
                    "author": "Dev",
                    "date": "3 hours ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "feature-diverged"
    assert result.ahead == 3
    assert result.behind == 5
    assert result.clean is True


def test_git_status_collector_no_upstream_branch(tmp_path: Path) -> None:
    """Test GitStatusCollector with no upstream tracking branch."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "new-branch"},
        file_statuses={worktree_path: ([], [], [])},
        # No ahead/behind info means no upstream
        ahead_behind={(worktree_path, "new-branch"): (0, 0)},
        recent_commits={worktree_path: []},
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "new-branch"
    assert result.ahead == 0
    assert result.behind == 0


def test_git_status_collector_with_stashes(tmp_path: Path) -> None:
    """Test GitStatusCollector behavior with stashes (not currently tracked)."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    # Note: Stash count is not currently tracked by GitStatus model
    git_ops = FakeGit(
        current_branches={worktree_path: "work-branch"},
        file_statuses={worktree_path: (["changes.py"], [], [])},
        ahead_behind={(worktree_path, "work-branch"): (1, 0)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "yz12345",
                    "message": "Work in progress",
                    "author": "Dev",
                    "date": "30 minutes ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "work-branch"
    assert len(result.staged_files) == 1


def test_git_status_collector_recent_commits(tmp_path: Path) -> None:
    """Test GitStatusCollector with multiple recent commits."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    commits = [
        {"sha": "abc1234", "message": "Latest commit", "author": "Alice", "date": "1 minute ago"},
        {"sha": "def5678", "message": "Previous work", "author": "Bob", "date": "1 hour ago"},
        {"sha": "ghi9012", "message": "Bug fix", "author": "Charlie", "date": "2 hours ago"},
        {"sha": "jkl3456", "message": "Feature addition", "author": "David", "date": "3 hours ago"},
        {"sha": "mno7890", "message": "Initial setup", "author": "Eve", "date": "1 day ago"},
    ]

    git_ops = FakeGit(
        current_branches={worktree_path: "active-development"},
        file_statuses={worktree_path: ([], [], [])},
        ahead_behind={(worktree_path, "active-development"): (5, 0)},
        recent_commits={worktree_path: commits},
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert len(result.recent_commits) == 5
    assert result.recent_commits[0].sha == "abc1234"
    assert result.recent_commits[0].message == "Latest commit"
    assert result.recent_commits[0].author == "Alice"
    assert result.recent_commits[0].date == "1 minute ago"
    assert result.recent_commits[4].sha == "mno7890"


def test_git_status_collector_in_detached_head(tmp_path: Path) -> None:
    """Test GitStatusCollector when in detached HEAD state."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    # Detached HEAD means no current branch
    git_ops = FakeGit(
        current_branches={worktree_path: None},  # Detached HEAD
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is None  # Should return None for detached HEAD


def test_git_status_collector_handles_subprocess_errors(tmp_path: Path) -> None:
    """Test GitStatusCollector gracefully handles subprocess errors."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    # Simulate error conditions by providing partial data
    git_ops = FakeGit(
        current_branches={worktree_path: "error-branch"},
        # No file_statuses entry means get_file_status returns ([], [], [])
        # No ahead_behind entry means get_ahead_behind returns (0, 0)
        # No recent_commits entry means get_recent_commits returns []
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert - should handle gracefully with defaults
    assert result is not None
    assert result.branch == "error-branch"
    assert result.clean is True  # No files means clean
    assert result.ahead == 0
    assert result.behind == 0
    assert len(result.staged_files) == 0
    assert len(result.modified_files) == 0
    assert len(result.untracked_files) == 0
    assert len(result.recent_commits) == 0


def test_git_status_collector_is_available(tmp_path: Path) -> None:
    """Test GitStatusCollector availability check."""
    # Arrange
    existing_path = tmp_path / "exists"
    existing_path.mkdir()
    nonexistent_path = tmp_path / "does_not_exist"

    git_ops = FakeGit()
    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act & Assert
    assert collector.is_available(ctx, existing_path) is True
    assert collector.is_available(ctx, nonexistent_path) is False


def test_git_status_collector_mixed_file_states(tmp_path: Path) -> None:
    """Test GitStatusCollector with files in multiple states."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    git_ops = FakeGit(
        current_branches={worktree_path: "complex-changes"},
        file_statuses={
            worktree_path: (
                ["staged1.py", "staged2.py"],  # Staged
                ["modified1.js", "modified2.css"],  # Modified
                ["new_file.txt", "temp.log"],  # Untracked
            )
        },
        ahead_behind={(worktree_path, "complex-changes"): (2, 3)},
        recent_commits={
            worktree_path: [
                {
                    "sha": "commit1",
                    "message": "Recent change",
                    "author": "Dev",
                    "date": "10 minutes ago",
                },
                {
                    "sha": "commit2",
                    "message": "Earlier change",
                    "author": "Dev",
                    "date": "20 minutes ago",
                },
            ]
        },
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert result.branch == "complex-changes"
    assert result.clean is False
    assert result.ahead == 2
    assert result.behind == 3
    assert len(result.staged_files) == 2
    assert len(result.modified_files) == 2
    assert len(result.untracked_files) == 2
    assert "staged1.py" in result.staged_files
    assert "modified1.js" in result.modified_files
    assert "new_file.txt" in result.untracked_files


def test_git_status_collector_limit_recent_commits(tmp_path: Path) -> None:
    """Test GitStatusCollector limits recent commits to 5."""
    # Arrange
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    repo_root = tmp_path / "repo"

    # Provide more than 5 commits
    commits = [
        {"sha": f"commit{i}", "message": f"Message {i}", "author": "Dev", "date": f"{i} hours ago"}
        for i in range(10)
    ]

    git_ops = FakeGit(
        current_branches={worktree_path: "many-commits"},
        file_statuses={worktree_path: ([], [], [])},
        ahead_behind={(worktree_path, "many-commits"): (10, 0)},
        recent_commits={worktree_path: commits},
    )

    ctx = create_test_context(git=git_ops)
    collector = GitStatusCollector()

    # Act
    result = collector.collect(ctx, worktree_path, repo_root)

    # Assert
    assert result is not None
    assert len(result.recent_commits) == 5  # Limited to 5
    assert result.recent_commits[0].sha == "commit0"
    assert result.recent_commits[4].sha == "commit4"
