"""Tests for git index lock waiting utilities."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.lock import get_lock_path, wait_for_index_lock
from erk_shared.gateway.time.fake import FakeTime


def create_git_repo(path: Path) -> None:
    """Create a minimal git repository at the given path."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )


class TestGetLockPath:
    """Tests for get_lock_path()."""

    def test_returns_lock_path_for_normal_repo(self, tmp_path: Path) -> None:
        """get_lock_path returns correct path for a normal repository."""
        repo = tmp_path / "repo"
        create_git_repo(repo)

        result = get_lock_path(repo)

        assert result is not None
        assert result == repo / ".git" / "index.lock"

    def test_returns_none_when_not_git_repo(self, tmp_path: Path) -> None:
        """get_lock_path returns None when not in a git repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        result = get_lock_path(non_repo)

        assert result is None

    def test_returns_worktree_specific_lock_path(self, tmp_path: Path) -> None:
        """get_lock_path returns the worktree-specific lock path, not main repo."""
        # Create main repo
        main_repo = tmp_path / "main"
        create_git_repo(main_repo)

        # Create an initial commit so we can create a worktree
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initial commit"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Create a worktree
        worktree = tmp_path / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree), "-b", "feature"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Get lock path for the worktree
        result = get_lock_path(worktree)

        assert result is not None
        # The lock path should be in the worktree's admin dir, NOT main repo
        # Worktree index.lock is at .git/worktrees/<name>/index.lock
        assert "worktrees" in str(result)
        assert result.name == "index.lock"
        # Verify it's NOT in the main repo's .git directly
        assert result != main_repo / ".git" / "index.lock"


class TestWaitForIndexLock:
    """Tests for wait_for_index_lock()."""

    def test_returns_true_when_no_lock_exists(self, tmp_path: Path) -> None:
        """wait_for_index_lock returns True immediately when no lock exists."""
        repo = tmp_path / "repo"
        create_git_repo(repo)
        fake_time = FakeTime()

        result = wait_for_index_lock(repo, fake_time)

        assert result is True
        # No sleeping should have occurred
        assert fake_time.sleep_calls == []

    def test_waits_and_returns_true_when_lock_released(self, tmp_path: Path) -> None:
        """wait_for_index_lock waits and returns True when lock is released."""
        repo = tmp_path / "repo"
        create_git_repo(repo)
        lock_file = repo / ".git" / "index.lock"
        lock_file.touch()
        fake_time = FakeTime()

        # Track sleep calls and delete lock after first sleep
        original_sleep = fake_time.sleep

        def sleep_and_remove_lock(seconds: float) -> None:
            original_sleep(seconds)
            if lock_file.exists():
                lock_file.unlink()

        fake_time.sleep = sleep_and_remove_lock  # type: ignore[method-assign]

        result = wait_for_index_lock(repo, fake_time)

        assert result is True
        # Should have slept once before lock was released
        assert fake_time.sleep_calls == [0.5]

    def test_returns_false_on_timeout(self, tmp_path: Path) -> None:
        """wait_for_index_lock returns False when lock is not released."""
        repo = tmp_path / "repo"
        create_git_repo(repo)
        lock_file = repo / ".git" / "index.lock"
        lock_file.touch()
        fake_time = FakeTime()

        result = wait_for_index_lock(
            repo,
            fake_time,
            max_wait_seconds=2.0,
            poll_interval=0.5,
        )

        assert result is False
        # Should have slept multiple times until timeout
        assert fake_time.sleep_calls == [0.5, 0.5, 0.5, 0.5]
        # Lock should still exist
        assert lock_file.exists()

    def test_respects_custom_poll_interval(self, tmp_path: Path) -> None:
        """wait_for_index_lock respects custom poll interval."""
        repo = tmp_path / "repo"
        create_git_repo(repo)
        lock_file = repo / ".git" / "index.lock"
        lock_file.touch()
        fake_time = FakeTime()

        wait_for_index_lock(
            repo,
            fake_time,
            max_wait_seconds=1.0,
            poll_interval=0.25,
        )

        # Should have slept with custom interval
        assert fake_time.sleep_calls == [0.25, 0.25, 0.25, 0.25]

    def test_returns_true_when_not_git_repo(self, tmp_path: Path) -> None:
        """wait_for_index_lock returns True when not in a git repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        fake_time = FakeTime()

        result = wait_for_index_lock(non_repo, fake_time)

        assert result is True
        # No sleeping should have occurred
        assert fake_time.sleep_calls == []

    def test_handles_worktree_lock(self, tmp_path: Path) -> None:
        """wait_for_index_lock waits on the worktree's own lock, not main repo."""
        # Create main repo
        main_repo = tmp_path / "main"
        create_git_repo(main_repo)

        # Create an initial commit
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Initial commit"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Create a worktree
        worktree = tmp_path / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree), "-b", "feature"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Get the worktree's lock path and create a lock there
        worktree_lock = get_lock_path(worktree)
        assert worktree_lock is not None
        worktree_lock.touch()

        fake_time = FakeTime()

        # Should timeout because the worktree-specific lock exists
        result = wait_for_index_lock(
            worktree,
            fake_time,
            max_wait_seconds=1.0,
            poll_interval=0.5,
        )

        assert result is False
        assert fake_time.sleep_calls == [0.5, 0.5]
