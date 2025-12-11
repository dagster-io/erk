import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from pygit2 import Blob, Commit, Tree

from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.github.context import with_pull_request_context
from csbot.local_context_store.github.types import PullRequestResult
from csbot.local_context_store.local_context_store import setup_fresh_github_repository


class TestGithubWorkingDirFunctions:
    """Test new GitHub working directory standalone functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    @patch("csbot.local_context_store.git.repository_operations.pygit2.clone_repository")
    @patch("csbot.local_context_store.git.repository_operations.clean_and_update_repository")
    @patch("csbot.local_context_store.git.repository_operations._fetch_repository")
    @patch(
        "csbot.local_context_store.git.repository_operations._fetch_repository_and_repoint_origin"
    )
    def test_setup_repo(self, mock_fetch_repoint, mock_fetch, mock_clean_update, mock_pygit2_clone):
        """Test setup_repo function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            repo_path = working_dir / "github-repo"

            # Mock clone_repository to create the directory as a side effect
            def mock_clone_side_effect(url, local_path, depth=None, callbacks=None):
                Path(local_path).mkdir(parents=True, exist_ok=True)

            mock_pygit2_clone.side_effect = mock_clone_side_effect

            setup_fresh_github_repository(self.github_config, repo_path)

            assert repo_path.exists()
            mock_pygit2_clone.assert_called_once()
            # clean_and_update_repository is only called if repo already exists
            mock_clean_update.assert_not_called()

    @patch("csbot.local_context_store.local_context_store.setup_fresh_github_repository")
    def test_repository_store_context(self, mock_setup):
        """Test repository store latest_file_tree context manager."""
        from csbot.local_context_store.local_context_store import create_local_context_store

        mock_tree = Mock()
        mock_store = create_local_context_store(self.github_config)

        # Mock the store's latest_file_tree method
        with patch.object(mock_store, "latest_file_tree") as mock_latest_file_tree:
            mock_latest_file_tree.return_value.__enter__.return_value = mock_tree
            mock_latest_file_tree.return_value.__exit__.return_value = None

            with mock_store.latest_file_tree() as tree:
                assert tree == mock_tree

    def test_latest_tree(self):
        """Test latest_file_tree context manager."""
        mock_tree = Mock()

        from csbot.local_context_store.local_context_store import create_local_context_store

        mock_store = create_local_context_store(self.github_config)

        # Mock the store's latest_file_tree method
        with patch.object(mock_store, "latest_file_tree") as mock_latest_file_tree:
            mock_tree_cm = Mock()
            mock_tree_cm.__enter__ = Mock(return_value=mock_tree)
            mock_tree_cm.__exit__ = Mock(return_value=None)
            mock_latest_file_tree.return_value = mock_tree_cm

            with mock_store.latest_file_tree() as tree:
                assert tree == mock_tree
                mock_latest_file_tree.assert_called_once()

    def test_with_pull_request_context(self):
        """Test with_pull_request_context function."""
        mock_repo_path = Path("/mock/repo")
        mock_repo = Mock()
        mock_repo.temp_repo_path = mock_repo_path
        mock_repo.commit_changes = Mock(return_value="feature-branch")
        mock_repo.create_pull_request = Mock(return_value="https://github.com/test/repo/pull/123")

        from csbot.local_context_store.local_context_store import create_local_context_store

        mock_store = create_local_context_store(self.github_config)

        # Mock the store's isolated_copy method
        with patch.object(mock_store, "isolated_copy") as mock_for_creating:
            mock_pr_cm = Mock()
            mock_pr_cm.__enter__ = Mock(return_value=mock_repo)
            mock_pr_cm.__exit__ = Mock(return_value=None)
            mock_for_creating.return_value = mock_pr_cm

            with with_pull_request_context(
                mock_store, "Test Title", "Test Body", False
            ) as pr_result:
                assert isinstance(pr_result, PullRequestResult)
                assert pr_result.repo_path == mock_repo_path
                assert pr_result.title == "Test Title"
                assert pr_result.body == "Test Body"
                assert pr_result.automerge is False

            # After exiting context, PR should be created
            assert pr_result.pr_url == "https://github.com/test/repo/pull/123"
            mock_repo.commit_changes.assert_called_once_with(
                "Test Title",
                author_name="csbot",
                author_email="csbot@example.com",
            )
            mock_repo.create_pull_request.assert_called_once_with(
                "Test Title", "Test Body", "feature-branch"
            )
            mock_for_creating.assert_called_once()

    def test_with_pull_request_context_automerge(self):
        """Test with_pull_request_context with automerge=True."""
        mock_repo_path = Path("/mock/repo")
        mock_repo = Mock()
        mock_repo.temp_repo_path = mock_repo_path
        mock_repo.commit_changes = Mock(return_value="feature-branch")
        mock_repo.create_and_merge_pull_request = Mock(
            return_value="https://github.com/test/repo/pull/123"
        )

        from csbot.local_context_store.local_context_store import create_local_context_store

        mock_store = create_local_context_store(self.github_config)

        # Mock the store's isolated_copy method
        with patch.object(mock_store, "isolated_copy") as mock_for_creating:
            mock_pr_cm = Mock()
            mock_pr_cm.__enter__ = Mock(return_value=mock_repo)
            mock_pr_cm.__exit__ = Mock(return_value=None)
            mock_for_creating.return_value = mock_pr_cm

            with with_pull_request_context(
                mock_store, "Auto Title", "Auto Body", True
            ) as pr_result:
                assert pr_result.automerge is True

            # Should use create_and_merge_pull_request for automerge
            assert pr_result.pr_url == "https://github.com/test/repo/pull/123"
            mock_repo.commit_changes.assert_called_once_with(
                "Auto Title",
                author_name="csbot",
                author_email="csbot@example.com",
            )
            mock_repo.create_and_merge_pull_request.assert_called_once_with(
                "Auto Title", "Auto Body", "feature-branch"
            )
            mock_for_creating.assert_called_once()

    def test_pull_request_result_properties(self):
        """Test PullRequestResult properties and aliases."""
        repo_path = Path("/test/repo")
        pr_result = PullRequestResult(repo_path, "Title", "Body", False)

        assert pr_result.repo_path == repo_path
        assert pr_result.repo_path == repo_path
        assert pr_result.title == "Title"
        assert pr_result.body == "Body"
        assert pr_result.automerge is False
        assert pr_result.pr_url is None  # Initially unset


class TestLocalBackedGithubContextStoreManager:
    """Test LocalBackedGithubContextStoreManager with real git operations."""

    def test_mutate_adds_cronjob_file(self):
        """Test mutate() properly serializes context store changes and commits them."""
        import asyncio

        import pygit2

        from csbot.contextengine.loader import load_context_store
        from csbot.contextengine.serializer import serialize_context_store
        from csbot.local_context_store.git.file_tree import FilesystemFileTree
        from csbot.local_context_store.local_context_store import (
            LocalBackedGithubContextStoreManager,
            create_local_context_store,
        )
        from tests.factories import context_store_builder

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test-repo"
            repo_path.mkdir()

            # Initialize a real git repository
            repo = pygit2.init_repository(str(repo_path), bare=False)

            # Create initial context store with just project config
            initial_context_store = context_store_builder().with_project("test/project").build()

            # Serialize initial state to filesystem
            serialize_context_store(initial_context_store, repo_path)

            # Create initial commit
            repo.index.add_all()
            repo.index.write()
            tree = repo.index.write_tree()
            author = pygit2.Signature("Test User", "test@example.com")
            repo.create_commit(
                "HEAD",
                author,
                author,
                "Initial commit",
                tree,
                [],
            )

            # Set up origin remote (mocked URL)
            repo.remotes.create("origin", "https://github.com/test/repo.git")

            # Create github config (with mock auth that won't actually push)
            github_config = GithubConfig.pat(token="fake_token", repo_name="test/repo")

            # Create local context store
            local_context_store = create_local_context_store(github_config, repo_path)

            # Mock isolated_copy to return an IsolatedContextStoreCopy pointing to the same path
            from contextlib import contextmanager

            from csbot.local_context_store.isolated_copy import IsolatedContextStoreCopy

            @contextmanager
            def mock_isolated_copy():
                yield IsolatedContextStoreCopy(repo_path, github_config)

            manager = LocalBackedGithubContextStoreManager(local_context_store, AsyncMock())

            # Load the "before" state
            tree_reader = FilesystemFileTree(repo_path)
            before = load_context_store(tree_reader)

            # Create "after" state with a new cronjob
            from csbot.contextengine.contextstore_protocol import UserCronJob

            after = before.model_copy(
                update={
                    "general_cronjobs": {
                        "daily_report": UserCronJob(
                            cron="0 9 * * *",
                            question="What happened yesterday?",
                            thread="daily-updates",
                        )
                    }
                }
            )

            # Mock _push_branch to avoid actual GitHub push
            with (
                patch(
                    "csbot.local_context_store.git.repository_operations._push_branch"
                ) as mock_push,
                # Also mock create_pull_request since we can't actually create PRs
                patch(
                    "csbot.local_context_store.isolated_copy.create_pull_request"
                ) as mock_create_pr,
                # Override isolated_copy to use our mock
                patch.object(local_context_store, "isolated_copy", side_effect=mock_isolated_copy),
            ):
                mock_create_pr.return_value = "https://github.com/test/repo/pull/123"

                # Call mutate
                import asyncio

                pr_url = asyncio.run(
                    manager.mutate(
                        title="Add daily report cron job",
                        body="Adding a daily report cronjob",
                        commit=False,
                        before=before,
                        after=after,
                    )
                )

            # Verify PR URL was returned
            assert pr_url == "https://github.com/test/repo/pull/123"

            # Verify _push_branch was called (meaning commit was created)
            assert mock_push.called

            # Verify the file was actually created in the isolated copy
            # The mutator should have created an isolated copy, so we need to check
            # that the serialization happened correctly by verifying the structure

            # Get the latest commit from the repo to verify changes
            head = repo.head
            commit = repo.get(head.target)
            assert isinstance(commit, Commit)

            # Verify commit message
            assert "Add daily report cron job" in commit.message

            # Verify the cronjobs.yaml file exists in the commit
            tree_obj = commit.tree
            cronjobs_dir = tree_obj / "cronjobs"
            assert isinstance(cronjobs_dir, Tree)
            cron_job_blob = cronjobs_dir / "daily_report.yaml"
            assert isinstance(cron_job_blob, Blob)
            assert cron_job_blob.size > 0
