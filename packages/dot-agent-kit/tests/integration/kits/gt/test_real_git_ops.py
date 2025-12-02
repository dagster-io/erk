"""Integration tests for real git/graphite operations using actual subprocess calls.

These tests verify that real subprocess-based implementations work correctly with
actual git and graphite commands. They create temporary repositories and execute
real operations to catch integration issues that mocks might miss.

Test organization:
- TestRealGitOperations: Git operations (6 tests with real git commands)
- TestRealGraphiteOperations: Graphite operations (2 tests with real gt commands)

Note: Git operations now use the core RealGit interface from erk_shared.git.real.
"""

import subprocess
import tempfile
from pathlib import Path

from erk_shared.git.real import RealGit


class TestRealGitOperations:
    """Integration tests for RealGit using real git subprocess calls."""

    def test_get_current_branch(self) -> None:
        """Test get_current_branch returns branch name with real git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Test from repo directory
            git = RealGit()
            branch_name = git.get_current_branch(repo_path)

            assert branch_name is not None
            assert isinstance(branch_name, str)
            # Default branch is typically "main" or "master"
            assert branch_name in ("main", "master")

    def test_has_uncommitted_changes(self) -> None:
        """Test has_uncommitted_changes detects changes correctly with real git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            git = RealGit()

            # Should be clean after commit
            assert git.has_uncommitted_changes(repo_path) is False

            # Create new file
            new_file = repo_path / "new.txt"
            new_file.write_text("new content", encoding="utf-8")

            # Should detect uncommitted changes
            assert git.has_uncommitted_changes(repo_path) is True

    def test_add_all(self) -> None:
        """Test add_all stages files correctly with real git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create file
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")

            git = RealGit()

            # Add all files (RealGit.add_all raises on failure, doesn't return bool)
            git.add_all(repo_path)

            # Verify files are staged by checking git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            # Staged new file shows as "A " (added to index)
            assert "A  test.txt" in result.stdout

    def test_commit(self) -> None:
        """Test commit creates commit correctly with real git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create and stage file
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)

            git = RealGit()

            # Create commit (RealGit.commit raises on failure, doesn't return bool)
            git.commit(repo_path, "Test commit")

            # Verify commit was created
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            assert "Test commit" in result.stdout

    def test_amend_commit(self) -> None:
        """Test amend_commit modifies commit correctly with real git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Modify file and stage
            test_file.write_text("modified", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)

            git = RealGit()

            # Amend commit (RealGit.amend_commit raises on failure, doesn't return bool)
            git.amend_commit(repo_path, "Amended commit")

            # Verify commit was amended
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            assert "Amended commit" in result.stdout

    def test_count_commits_ahead(self) -> None:
        """Test count_commits_ahead counts correctly with real git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create initial commit on main
            test_file = repo_path / "test.txt"
            test_file.write_text("test", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Rename default branch to main (git init may create master or other name)
            subprocess.run(
                ["git", "branch", "-M", "main"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Create branch and add commits
            subprocess.run(
                ["git", "checkout", "-b", "feature"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            for i in range(3):
                new_file = repo_path / f"file{i}.txt"
                new_file.write_text(f"content{i}", encoding="utf-8")
                subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Commit {i}"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )

            git = RealGit()

            # Count commits since main
            count = git.count_commits_ahead(repo_path, "main")

            assert isinstance(count, int)
            assert count == 3


class TestRealGraphiteOperations:
    """Integration tests for RealGraphiteGtKit using real gt subprocess calls.

    These tests call real gt commands and verify they don't crash.
    Tests may fail if gt is not installed, which is expected behavior.
    """
