"""Integration tests for real git/graphite operations using actual subprocess calls.

These tests verify that real subprocess-based implementations work correctly with
actual git and graphite commands. They create temporary repositories and execute
real operations to catch integration issues that mocks might miss.

Test organization:
- TestRealGitOperations: Git operations (6 tests with real git commands)
- TestRealGraphiteOperations: Graphite operations (2 tests with real gt commands)
"""

import os
import subprocess
import tempfile
from pathlib import Path

from erk_shared.integrations.gt.real import RealGitGtKit


class TestRealGitOperations:
    """Integration tests for RealGitGtKit using real git subprocess calls."""

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
            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKit()
                branch_name = ops.get_current_branch()

                assert branch_name is not None
                assert isinstance(branch_name, str)
                # Default branch is typically "main" or "master"
                assert branch_name in ("main", "master")
            finally:
                os.chdir(original_cwd)

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

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKit()

                # Should be clean after commit
                assert ops.has_uncommitted_changes() is False

                # Create new file
                new_file = repo_path / "new.txt"
                new_file.write_text("new content", encoding="utf-8")

                # Should detect uncommitted changes
                assert ops.has_uncommitted_changes() is True
            finally:
                os.chdir(original_cwd)

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

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKit()

                # Add all files
                result = ops.add_all()

                assert result is True
            finally:
                os.chdir(original_cwd)

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

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKit()

                # Create commit
                result = ops.commit("Test commit")

                assert result is True
            finally:
                os.chdir(original_cwd)

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

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKit()

                # Amend commit
                result = ops.amend_commit("Amended commit")

                assert result is True
            finally:
                os.chdir(original_cwd)

    def test_count_commits_in_branch(self) -> None:
        """Test count_commits_in_branch counts correctly with real git."""
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

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                ops = RealGitGtKit()

                # Count commits since main
                count = ops.count_commits_in_branch("main")

                assert isinstance(count, int)
                assert count == 3
            finally:
                os.chdir(original_cwd)


class TestRealGraphiteOperations:
    """Integration tests for RealGraphiteGtKit using real gt subprocess calls.

    These tests call real gt commands and verify they don't crash.
    Tests may fail if gt is not installed, which is expected behavior.
    """
