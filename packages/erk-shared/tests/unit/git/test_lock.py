"""Tests for git index lock waiting utilities."""

from pathlib import Path

from erk_shared.gateway.time.fake import FakeTime
from erk_shared.git.lock import get_git_dir, wait_for_index_lock


class TestGetGitDir:
    """Tests for get_git_dir()."""

    def test_returns_git_path_for_normal_repo(self, tmp_path: Path) -> None:
        """get_git_dir returns .git directory for a normal repository."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = get_git_dir(tmp_path)

        assert result == git_dir

    def test_returns_path_when_git_does_not_exist(self, tmp_path: Path) -> None:
        """get_git_dir returns expected path even when .git doesn't exist."""
        result = get_git_dir(tmp_path)

        assert result == tmp_path / ".git"

    def test_follows_worktree_indirection(self, tmp_path: Path) -> None:
        """get_git_dir follows gitdir pointer for worktrees."""
        # Set up main repo structure
        main_repo = tmp_path / "main-repo"
        main_git = main_repo / ".git"
        main_git.mkdir(parents=True)
        worktrees_dir = main_git / "worktrees" / "feature"
        worktrees_dir.mkdir(parents=True)

        # Set up worktree with gitdir pointer
        worktree = tmp_path / "worktrees" / "feature"
        worktree.mkdir(parents=True)
        worktree_git_file = worktree / ".git"
        worktree_git_file.write_text(f"gitdir: {worktrees_dir}", encoding="utf-8")

        result = get_git_dir(worktree)

        # Should return main .git, not worktree subdir
        assert result == main_git

    def test_handles_worktree_gitdir_not_existing(self, tmp_path: Path) -> None:
        """get_git_dir handles case where gitdir target doesn't exist."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        worktree_git_file = worktree / ".git"
        worktree_git_file.write_text("gitdir: /nonexistent/path/.git/worktrees/x", encoding="utf-8")

        result = get_git_dir(worktree)

        # Should fall back to the .git file path
        assert result == worktree_git_file


class TestWaitForIndexLock:
    """Tests for wait_for_index_lock()."""

    def test_returns_true_when_no_lock_exists(self, tmp_path: Path) -> None:
        """wait_for_index_lock returns True immediately when no lock exists."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        fake_time = FakeTime()

        result = wait_for_index_lock(tmp_path, fake_time)

        assert result is True
        # No sleeping should have occurred
        assert fake_time.sleep_calls == []

    def test_waits_and_returns_true_when_lock_released(self, tmp_path: Path) -> None:
        """wait_for_index_lock waits and returns True when lock is released."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.touch()
        fake_time = FakeTime()

        # Track sleep calls and delete lock after first sleep
        original_sleep = fake_time.sleep

        def sleep_and_remove_lock(seconds: float) -> None:
            original_sleep(seconds)
            if lock_file.exists():
                lock_file.unlink()

        fake_time.sleep = sleep_and_remove_lock  # type: ignore[method-assign]

        result = wait_for_index_lock(tmp_path, fake_time)

        assert result is True
        # Should have slept once before lock was released
        assert fake_time.sleep_calls == [0.5]

    def test_returns_false_on_timeout(self, tmp_path: Path) -> None:
        """wait_for_index_lock returns False when lock is not released."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.touch()
        fake_time = FakeTime()

        result = wait_for_index_lock(
            tmp_path,
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
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.touch()
        fake_time = FakeTime()

        wait_for_index_lock(
            tmp_path,
            fake_time,
            max_wait_seconds=1.0,
            poll_interval=0.25,
        )

        # Should have slept with custom interval
        assert fake_time.sleep_calls == [0.25, 0.25, 0.25, 0.25]

    def test_handles_worktree_lock(self, tmp_path: Path) -> None:
        """wait_for_index_lock waits on main repo lock for worktrees."""
        # Set up main repo with lock
        main_repo = tmp_path / "main-repo"
        main_git = main_repo / ".git"
        main_git.mkdir(parents=True)
        lock_file = main_git / "index.lock"
        lock_file.touch()
        worktrees_dir = main_git / "worktrees" / "feature"
        worktrees_dir.mkdir(parents=True)

        # Set up worktree with gitdir pointer
        worktree = tmp_path / "worktrees" / "feature"
        worktree.mkdir(parents=True)
        worktree_git_file = worktree / ".git"
        worktree_git_file.write_text(f"gitdir: {worktrees_dir}", encoding="utf-8")

        fake_time = FakeTime()

        # Should timeout since lock is on main repo
        result = wait_for_index_lock(
            worktree,
            fake_time,
            max_wait_seconds=1.0,
            poll_interval=0.5,
        )

        assert result is False
        assert fake_time.sleep_calls == [0.5, 0.5]
