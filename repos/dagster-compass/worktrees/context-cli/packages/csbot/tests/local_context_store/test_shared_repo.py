"""Tests for SharedRepo class with time provider integration."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.local_context_store import RepoConfig, SharedRepo
from csbot.utils.time import DatetimeNowFake


@pytest.fixture
def github_config():
    """Create a test GitHub configuration."""
    return GithubConfig.pat(token="test_token", repo_name="test/repo")


@pytest.fixture
def temp_base_path():
    """Create a temporary base path for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def controlled_datetime_now():
    """Create a controlled datetime now provider for testing."""
    # Start at epoch time 1000000
    return DatetimeNowFake(initial_time_seconds=1000000)


@pytest.fixture
def repo_config(github_config, temp_base_path):
    """Create a test RepoConfig."""
    return RepoConfig(github_config=github_config, base_path=temp_base_path)


class TestSharedRepoRefreshTiming:
    """Test SharedRepo refresh timing logic."""

    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_initial_refresh_forced(self, mock_ensure_repo, repo_config, controlled_datetime_now):
        """Test that first access always triggers refresh (datetime.min)."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
            datetime_now=controlled_datetime_now,
        )

        # Create the repo directory so it exists
        shared_repo.repo_path.mkdir(parents=True, exist_ok=True)

        # Call refresh_if_needed - should refresh due to datetime.min
        shared_repo.refresh_if_needed()

        # Verify ensure_github_repository was called
        mock_ensure_repo.assert_called_once_with(repo_config)

    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_refresh_after_interval(self, mock_ensure_repo, repo_config, controlled_datetime_now):
        """Test refresh occurs after 1 minute interval."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
            datetime_now=controlled_datetime_now,
        )

        # Create the repo directory
        shared_repo.repo_path.mkdir(parents=True, exist_ok=True)

        # First refresh
        shared_repo.refresh_if_needed()
        assert mock_ensure_repo.call_count == 1

        # Advance time by 61 seconds (past 1 minute threshold)
        controlled_datetime_now.advance_time(61)

        # Second refresh should occur
        shared_repo.refresh_if_needed()
        assert mock_ensure_repo.call_count == 2

    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_no_refresh_within_interval(
        self, mock_ensure_repo, repo_config, controlled_datetime_now
    ):
        """Test no refresh occurs within 1 minute interval."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
            datetime_now=controlled_datetime_now,
        )

        # Create the repo directory
        shared_repo.repo_path.mkdir(parents=True, exist_ok=True)

        # First refresh
        shared_repo.refresh_if_needed()
        assert mock_ensure_repo.call_count == 1

        # Advance time by 59 seconds (still within 1 minute)
        controlled_datetime_now.advance_time(59)

        # Second call should not refresh
        shared_repo.refresh_if_needed()
        assert mock_ensure_repo.call_count == 1  # Still 1, no new call

    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_missing_repo_triggers_refresh(
        self, mock_ensure_repo, repo_config, controlled_datetime_now
    ):
        """Test refresh occurs when repo doesn't exist, even within interval."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
            datetime_now=controlled_datetime_now,
        )

        # First refresh (repo doesn't exist)
        shared_repo.refresh_if_needed()
        assert mock_ensure_repo.call_count == 1

        # Advance time by only 30 seconds (within interval)
        controlled_datetime_now.advance_time(30)

        # Repo still doesn't exist, should refresh again
        shared_repo.refresh_if_needed()
        assert mock_ensure_repo.call_count == 2

    @patch("csbot.local_context_store.local_context_store.clean_and_update_repository")
    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_force_refresh_always_refreshes(
        self,
        mock_ensure_repo,
        mock_clean_update,
        repo_config,
        controlled_datetime_now,
    ):
        """Test force_refresh always updates regardless of time."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
            datetime_now=controlled_datetime_now,
        )

        # Create the repo directory
        shared_repo.repo_path.mkdir(parents=True, exist_ok=True)

        # Force refresh multiple times without advancing time
        shared_repo.force_refresh()
        assert mock_ensure_repo.call_count == 1
        assert mock_clean_update.call_count == 1

        shared_repo.force_refresh()
        assert mock_ensure_repo.call_count == 2
        assert mock_clean_update.call_count == 2

        # Force refresh works even immediately after
        shared_repo.force_refresh()
        assert mock_ensure_repo.call_count == 3
        assert mock_clean_update.call_count == 3


class TestSharedRepoLocking:
    """Test SharedRepo locking behavior."""

    def test_lock_file_creation(self, repo_config):
        """Test lock file is created in correct location."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
        )

        expected_lock_path = repo_config.base_path / "repo.lock"
        assert shared_repo.lock_file == expected_lock_path

    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    @patch("fcntl.flock")
    def test_lock_acquired_and_released(self, mock_flock, mock_ensure_repo, repo_config):
        """Test lock is acquired and released properly."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
        )

        # Create the repo directory
        shared_repo.repo_path.mkdir(parents=True, exist_ok=True)

        # Call refresh_if_needed which uses locking
        shared_repo.refresh_if_needed()

        # Verify flock was called twice (acquire and release)
        assert mock_flock.call_count == 2
        # First call should be LOCK_EX (exclusive lock)
        import fcntl

        assert mock_flock.call_args_list[0][0][1] == fcntl.LOCK_EX
        # Second call should be LOCK_UN (unlock)
        assert mock_flock.call_args_list[1][0][1] == fcntl.LOCK_UN

    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    @patch("fcntl.flock")
    def test_lock_released_on_exception(self, mock_flock, mock_ensure_repo, repo_config):
        """Test lock is released even when an exception occurs."""
        mock_ensure_repo.side_effect = Exception("Test exception")

        shared_repo = SharedRepo(
            repo_config=repo_config,
        )

        # This should raise but still release the lock
        with pytest.raises(Exception, match="Test exception"):
            shared_repo.refresh_if_needed()

        # Verify flock was still called to release
        assert mock_flock.call_count == 2
        import fcntl

        assert mock_flock.call_args_list[1][0][1] == fcntl.LOCK_UN


class TestSharedRepoProperties:
    """Test SharedRepo property calculations."""

    def test_repo_path_calculation(self, repo_config):
        """Test repo_path is correctly calculated from base_path and config."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
        )

        expected_path = repo_config.base_path / "repo"
        assert shared_repo.repo_path == expected_path

    def test_lock_file_path_calculation(self, repo_config):
        """Test lock_file path is correctly calculated."""
        shared_repo = SharedRepo(
            repo_config=repo_config,
        )

        expected_lock = repo_config.base_path / "repo.lock"
        assert shared_repo.lock_file == expected_lock
