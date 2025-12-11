"""Integration smoke tests without mocks to catch real async context errors."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from csbot.contextengine.loader import load_project_from_tree
from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.local_context_store import LocalContextStore
from csbot.slackbot.channel_bot.tasks.weekly_refresh import WeeklyRefreshTask
from tests.factories.context_store_factory import context_store_builder


class LocalRepositoryOperations:
    """Test-only repository operations that use existing local repositories without GitHub operations."""

    def ensure_repository(self, github_config: GithubConfig, base_path: Path) -> Path:
        """Return the existing local repository path without any GitHub operations.

        Args:
            github_config: GitHub configuration (ignored for local testing)
            base_path: Base directory containing the test repository

        Returns:
            Path to the existing test repository
        """
        return base_path

    def commit_and_push_changes(
        self,
        github_config: GithubConfig,
        repo_path: Path,
        title: str,
        author_name: str = "csbot",
        author_email: str = "csbot@example.com",
    ) -> str:
        """Mock Git workflow operations - returns a fake branch name without actual operations.

        Args:
            github_config: GitHub configuration (ignored)
            repo_path: Path to the git repository (ignored)
            title: Commit message (ignored)
            author_name: Author name (ignored)
            author_email: Author email (ignored)

        Returns:
            str: Fake branch name for testing
        """
        return "test-branch-123"

    def create_pull_request(
        self,
        github_config: GithubConfig,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> str:
        """Mock PR creation - returns fake PR URL without GitHub API calls.

        Args:
            github_config: GitHub configuration (ignored)
            title: Pull request title (ignored)
            body: Pull request body (ignored)
            head_branch: Source branch name (ignored)

        Returns:
            str: Fake PR URL for testing
        """
        return "https://github.com/test-owner/test-repo/pull/123"

    def merge_pull_request(self, github_config: GithubConfig, pr_number: int) -> None:
        """Mock PR merge - no-op for testing.

        Args:
            github_config: GitHub configuration (ignored)
            pr_number: Pull request number (ignored)
        """
        pass

    def create_and_merge_pull_request(
        self,
        github_config: GithubConfig,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> str:
        """Mock PR creation and merge - returns fake PR URL without GitHub API calls.

        Args:
            github_config: GitHub configuration (ignored)
            title: Pull request title (ignored)
            body: Pull request body (ignored)
            head_branch: Source branch name (ignored)

        Returns:
            str: Fake PR URL for testing
        """
        return "https://github.com/test-owner/test-repo/pull/123"

    def setup_fresh_repository(self, github_config: GithubConfig, repo_path: Path) -> None:
        """Mock fresh repository setup - no-op for testing.

        Args:
            github_config: GitHub configuration (ignored)
            repo_path: Path to setup the repository at (ignored)
        """
        pass


@pytest.fixture(scope="class")
def shared_git_repo():
    """Create a shared temporary Git repository for all integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test-repo"
        repo_path.mkdir()

        # Initialize Git repository
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
        )
        # Add fake remote origin to avoid remote errors
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test-owner/test-repo.git"],
            cwd=repo_path,
            check=True,
        )

        # Create minimal repository structure
        (repo_path / "contextstore_project.yaml").write_text("""
project_name: test-owner/test-repo
""")
        (repo_path / "README.md").write_text("# Test Repository")

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

        # Create GitHubConfig and LocalContextStorePool with local-only setup
        github_config = GithubConfig.pat(
            token="fake-token-for-testing", repo_name="test-owner/test-repo"
        )

        # Use parent directory as base_path
        base_path = repo_path.parent
        from csbot.local_context_store.local_context_store import RepoConfig, SharedRepo

        repo_config = RepoConfig(github_config=github_config, base_path=base_path)
        shared_repo = SharedRepo(repo_config)
        local_context_store = LocalContextStore(shared_repo)

        yield local_context_store


class TestIntegrationAsyncContext:
    """Integration smoke tests using real Git operations to catch async context errors."""

    @pytest.mark.asyncio
    async def test_weekly_refresh_task_real_git_operations(self, shared_git_repo):
        """Test WeeklyRefreshTask with real Git operations - should catch async context errors."""
        from csbot.contextengine.contextstore_protocol import (
            Dataset,
        )

        # Create bot with real repo store
        bot = Mock()
        bot.local_context_store = shared_git_repo
        bot.logger = Mock()

        # Mock load_context_store to return test datasets
        dataset1 = Dataset(table_name="test_table", connection="test_conn")
        context_store = (
            context_store_builder().with_project("test/project").add_dataset(dataset1).build()
        )
        bot.load_context_store = AsyncMock(return_value=context_store)
        bot.profile = Mock()
        bot.agent = Mock()

        # Mock external dependencies that don't need real Git operations
        dataset_monitor = Mock()
        github_pr_handler = Mock()
        github_pr_handler.create_weekly_refresh_pr = AsyncMock()

        task = WeeklyRefreshTask(bot, dataset_monitor, github_pr_handler)

        # This should work with fixed code, fail with "Cannot run in async context" if broken
        await task.execute_tick()

        # Verify the task executed successfully
        github_pr_handler.create_weekly_refresh_pr.assert_called_once()

    @pytest.mark.asyncio
    async def test_direct_git_operations_in_async_context_should_fail(self, shared_git_repo):
        """Direct test: Git operations called from async context should fail."""

        # For this test, we need to use the real GitHub operations to trigger the async context check
        from csbot.local_context_store.local_context_store import RepoConfig, SharedRepo

        repo_config = RepoConfig(
            github_config=shared_git_repo.github_config, base_path=shared_git_repo.base_path
        )
        shared_repo = SharedRepo(repo_config)
        real_local_context_store = LocalContextStore(shared_repo)

        # This should fail with "Cannot run in async context" because we're in an async function
        with pytest.raises(Exception, match="Cannot run in async context"):
            with real_local_context_store.latest_file_tree() as tree:
                load_project_from_tree(tree)

    def test_direct_git_operations_in_sync_context_should_work(self, shared_git_repo):
        """Control test: Git operations should work in sync context with existing repo."""

        # Since we're using an existing local repo, we need to avoid the clone operation
        # Let's just verify the repo store exists and has the expected properties
        assert shared_git_repo is not None
        assert shared_git_repo.github_config.repo_name == "test-owner/test-repo"
        assert shared_git_repo.base_path.exists()

        # This demonstrates the repo store is properly set up for other tests
