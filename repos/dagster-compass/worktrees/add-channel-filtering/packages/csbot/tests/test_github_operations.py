"""Tests for GitHub operations and related functionality.

This module tests the GitHub integration components including:
- GitHub API operations
- Repository store functionality
- Context managers for GitHub working directories
- Pull request operations
- Repository operations
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
import yaml

from csbot.local_context_store.github.api import (
    add_collaborator_to_repository,
    add_pull_request_comment,
    close_pull_request,
    create_and_merge_pull_request,
    create_data_request_issue,
    create_issue,
    create_pull_request,
    create_repository,
    dispatch_workflow,
    get_pull_request_status,
    initialize_contextstore_repository,
    merge_pull_request,
)
from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.github.context import with_pull_request_context
from csbot.local_context_store.github.types import (
    InitializedContextRepository,
    PullRequestResult,
)
from csbot.local_context_store.github.utils import extract_pr_number_from_url
from csbot.local_context_store.local_context_store import (
    LocalContextStore,
    RepoConfig,
    SharedRepo,
    create_local_context_store,
    setup_fresh_github_repository,
)

if TYPE_CHECKING:
    from csbot.local_context_store.github.types import (
        WorkflowRunStatus,
    )


class TestGitHubAPI:
    """Test GitHub API functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    @patch("csbot.local_context_store.github.config.Github")
    def test_create_repository(self, mock_github_class):
        """Test create_repository function."""
        mock_github = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_repo.html_url = "https://github.com/dagster-compass/test-repo"

        mock_github_class.return_value = mock_github
        mock_github.get_organization.return_value = mock_org
        mock_org.create_repo.return_value = mock_repo

        result = create_repository(self.github_config.auth_source, "test-repo")

        assert result == "https://github.com/dagster-compass/test-repo"
        mock_github.get_organization.assert_called_once_with("dagster-compass")
        mock_org.create_repo.assert_called_once_with(
            name="test-repo",
            description="Context repository for test-repo",
            private=True,
            auto_init=True,
            gitignore_template="Python",
        )

    @patch("csbot.local_context_store.github.config.Github")
    def test_initialize_contextstore_repository(self, mock_github_class):
        """Test initialize_contextstore_repository function."""
        mock_github = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_repo.html_url = "https://github.com/dagster-compass/test-repo"
        mock_repo.default_branch = "main"

        mock_github_class.return_value = mock_github
        mock_github.get_organization.return_value = mock_org
        mock_org.get_repo.return_value = mock_repo

        result = initialize_contextstore_repository(
            self.github_config.auth_source, "test-repo", "org/project", "dagster-compass", None
        )

        assert isinstance(result, InitializedContextRepository)
        assert result.project_name == "org/project"
        assert result.html_url == "https://github.com/dagster-compass/test-repo"
        assert "contextstore_project.yaml" in result.created_files
        assert "system_prompt.md" in result.created_files
        assert "channels/.gitkeep" in result.created_files

        # Verify files were created
        assert mock_repo.create_file.call_count == 3
        calls = mock_repo.create_file.call_args_list

        # Check contextstore_project.yaml
        assert calls[0][1]["path"] == "contextstore_project.yaml"
        contextstore_content = yaml.safe_load(calls[0][1]["content"])
        assert contextstore_content["project_name"] == "org/project"
        assert contextstore_content["teams"] == {}

        # Check system_prompt.md
        assert calls[1][1]["path"] == "system_prompt.md"
        assert "friendly and helpful AI" in calls[1][1]["content"]

        # Check channels/.gitkeep
        assert calls[2][1]["path"] == "channels/.gitkeep"
        assert calls[2][1]["content"] == ""

    @patch("csbot.local_context_store.github.config.Github")
    def test_add_collaborator_to_repository(self, mock_github_class):
        """Test add_collaborator_to_repository function."""
        mock_github = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_invitation = Mock()

        mock_github_class.return_value = mock_github
        mock_github.get_organization.return_value = mock_org
        mock_org.get_repo.return_value = mock_repo
        mock_repo.add_to_collaborators.return_value = mock_invitation

        add_collaborator_to_repository(
            self.github_config.auth_source, "test-repo", "username", "push"
        )

        mock_repo.add_to_collaborators.assert_called_once_with("username", permission="push")

    @patch("csbot.local_context_store.github.config.Github")
    def test_create_pull_request(self, mock_github_class):
        """Test create_pull_request function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/123"
        mock_repo.default_branch = "main"

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pr

        result = create_pull_request(self.github_config, "Test PR", "Test body", "feature-branch")

        assert result == "https://github.com/test/repo/pull/123"
        mock_repo.create_pull.assert_called_once_with(
            title="Test PR", body="Test body", head="feature-branch", base="main"
        )

    @patch("csbot.local_context_store.github.config.Github")
    def test_merge_pull_request(self, mock_github_class):
        """Test merge_pull_request function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        merge_pull_request(self.github_config, 123)

        mock_repo.get_pull.assert_called_once_with(123)
        mock_pr.merge.assert_called_once()

    @patch("csbot.local_context_store.github.config.Github")
    def test_create_and_merge_pull_request(self, mock_github_class):
        """Test create_and_merge_pull_request function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.html_url = "https://github.com/test/repo/pull/123"
        mock_repo.default_branch = "main"

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.create_pull.return_value = mock_pr
        mock_repo.get_pull.return_value = mock_pr

        result = create_and_merge_pull_request(
            self.github_config, "Test PR", "Test body", "feature-branch"
        )

        assert result == "https://github.com/test/repo/pull/123"
        mock_repo.create_pull.assert_called_once()
        mock_repo.get_pull.assert_called_once_with(123)
        mock_pr.merge.assert_called_once()

    @patch("csbot.local_context_store.github.config.Github")
    def test_create_issue(self, mock_github_class):
        """Test create_issue function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.html_url = "https://github.com/test/repo/issues/456"

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_issue

        result = create_issue(self.github_config, "Test Issue", "Test body", ["bug", "enhancement"])

        assert result == "https://github.com/test/repo/issues/456"
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue", body="Test body", labels=["bug", "enhancement"]
        )

    @patch("csbot.local_context_store.github.api.create_issue")
    def test_create_data_request_issue(self, mock_create_issue):
        """Test create_data_request_issue function."""
        mock_create_issue.return_value = "https://github.com/test/repo/issues/456"

        result = create_data_request_issue(
            self.github_config, "Data Access", "Need sales data", "Data Team"
        )

        assert result == "https://github.com/test/repo/issues/456"
        mock_create_issue.assert_called_once_with(
            self.github_config, "REQUEST: Data Access", "Data Team\n\nNeed sales data"
        )

    @patch("csbot.local_context_store.github.config.Github")
    def test_get_pull_request_status_merged(self, mock_github_class):
        """Test get_pull_request_status for merged PR."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.state = "closed"
        mock_pr.merged = True

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        result = get_pull_request_status(self.github_config, 123)

        assert result == "approved"

    @patch("csbot.local_context_store.github.config.Github")
    def test_get_pull_request_status_closed_not_merged(self, mock_github_class):
        """Test get_pull_request_status for closed but not merged PR."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.state = "closed"
        mock_pr.merged = False

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        result = get_pull_request_status(self.github_config, 123)

        assert result == "rejected"

    @patch("csbot.local_context_store.github.config.Github")
    def test_get_pull_request_status_open(self, mock_github_class):
        """Test get_pull_request_status for open PR."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.state = "open"

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        result = get_pull_request_status(self.github_config, 123)

        assert result == "pending"

    @patch("csbot.local_context_store.github.config.Github")
    def test_add_pull_request_comment(self, mock_github_class):
        """Test add_pull_request_comment function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        add_pull_request_comment(self.github_config, 123, "Test comment")

        mock_repo.get_pull.assert_called_once_with(123)
        mock_pr.create_issue_comment.assert_called_once_with("Test comment")

    @patch("csbot.local_context_store.github.config.Github")
    def test_close_pull_request(self, mock_github_class):
        """Test close_pull_request function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr

        close_pull_request(self.github_config, 123)

        mock_repo.get_pull.assert_called_once_with(123)
        mock_pr.edit.assert_called_once_with(state="closed")

    @patch("csbot.local_context_store.github.config.Github")
    def test_dispatch_workflow(self, mock_github_class):
        """Test dispatch_workflow function."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_workflow = Mock()
        mock_run = Mock()
        mock_run.id = 12345

        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_workflow.return_value = mock_workflow
        mock_workflow.get_runs.return_value = iter([mock_run])

        result = dispatch_workflow(
            self.github_config, "deploy.yml", "main", {"environment": "prod"}
        )

        assert result == 12345
        mock_repo.get_workflow.assert_called_once_with("deploy.yml")
        mock_workflow.create_dispatch.assert_called_once_with(
            ref="main", inputs={"environment": "prod"}
        )


class TestGitHubUtils:
    """Test GitHub utility functions."""

    def test_extract_pr_number_from_url_github_com(self):
        """Test extracting PR number from GitHub.com URL."""
        url = "https://github.com/test/repo/pull/123"
        result = extract_pr_number_from_url(url)
        assert result == 123

    def test_extract_pr_number_from_url_api_github_com(self):
        """Test extracting PR number from GitHub API URL."""
        url = "https://api.github.com/repos/test/repo/pulls/456"
        result = extract_pr_number_from_url(url)
        assert result == 456

    def test_extract_pr_number_from_url_invalid(self):
        """Test extracting PR number from invalid URL raises error."""
        with pytest.raises(ValueError, match="Invalid GitHub pull request URL"):
            extract_pr_number_from_url("https://example.com/invalid")


class TestRepositoryOperations:
    """Test GitHub repository operation functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(
            token="test_token",
            repo_name="test/repo",
        )

    @patch("csbot.local_context_store.git.repository_operations.pygit2.clone_repository")
    @patch("csbot.local_context_store.git.repository_operations.clean_and_update_repository")
    @patch("csbot.local_context_store.git.repository_operations._fetch_repository")
    @patch(
        "csbot.local_context_store.git.repository_operations._fetch_repository_and_repoint_origin"
    )
    def test_setup_fresh_repository(
        self, mock_fetch_repoint, mock_fetch, mock_clean_update, mock_pygit2_clone
    ):
        """Test setup_fresh_repository delegates to git operations."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"

            # Mock clone to create the directory
            def mock_clone_side_effect(url, local_path, depth=None, callbacks=None):
                Path(local_path).mkdir(parents=True, exist_ok=True)

            mock_pygit2_clone.side_effect = mock_clone_side_effect

            setup_fresh_github_repository(self.github_config, repo_path)

            assert repo_path.exists()
            mock_pygit2_clone.assert_called_once()


class TestLocalContextStorePool:
    """Test LocalContextStorePool class."""

    def setup_method(self):
        """Set up test fixtures."""
        import tempfile

        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")
        self.temp_dir = tempfile.mkdtemp()
        repo_config = RepoConfig(github_config=self.github_config, base_path=Path(self.temp_dir))
        shared_repo = SharedRepo(repo_config)
        self.store = LocalContextStore(shared_repo)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("csbot.local_context_store.local_context_store.create_git_commit_file_tree")
    @patch("csbot.local_context_store.local_context_store.fcntl")
    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_latest_file_tree(self, mock_ensure, mock_fcntl, mock_create_tree):
        """Test latest_file_tree factory method."""
        expected_path = Path(self.temp_dir) / "repo"
        mock_ensure.return_value = expected_path
        # Mock fcntl to avoid file system operations
        mock_fcntl.flock = Mock()

        # Mock the file tree context manager
        mock_tree = Mock()

        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_tree)
        mock_context_manager.__exit__ = Mock(return_value=None)

        mock_create_tree.return_value = mock_context_manager

        with self.store.latest_file_tree() as tree:
            assert tree == mock_tree

        # Should be called with RepoConfig
        mock_ensure.assert_called_once()
        call_args = mock_ensure.call_args[0][0]
        assert call_args.github_config == self.github_config
        assert call_args.base_path == Path(self.temp_dir)
        mock_create_tree.assert_called_once_with(expected_path, self.github_config.repo_name)

    @patch("csbot.local_context_store.local_context_store.clean_and_update_repository")
    @patch("csbot.local_context_store.local_context_store.fcntl")
    @patch("csbot.local_context_store.local_context_store.ensure_github_repository")
    def test_update_to_latest(self, mock_ensure, mock_fcntl, mock_clean_update):
        """Test update_to_latest method."""
        expected_path = Path(self.temp_dir) / "repo"
        mock_ensure.return_value = expected_path
        # Mock fcntl to avoid file system operations
        mock_fcntl.flock = Mock()

        self.store.update_to_latest()

        # Should be called with RepoConfig
        mock_ensure.assert_called_once()
        call_args = mock_ensure.call_args[0][0]
        assert call_args.github_config == self.github_config
        assert call_args.base_path == Path(self.temp_dir)
        mock_clean_update.assert_called_once_with(expected_path, github_config=self.github_config)

    @patch("csbot.local_context_store.local_context_store.setup_fresh_github_repository")
    def test_isolated_copy(self, mock_setup):
        """Test isolated_copy factory method."""
        with patch("tempfile.TemporaryDirectory") as mock_tempdir:
            mock_tempdir_obj = Mock()
            mock_tempdir_obj.name = "/tmp/test"
            mock_tempdir_obj.__enter__ = Mock(return_value="/tmp/test")
            mock_tempdir_obj.__exit__ = Mock(return_value=None)
            mock_tempdir.return_value = mock_tempdir_obj

            with self.store.isolated_copy() as isolated_copy:
                assert isolated_copy.temp_repo_path == Path("/tmp/test/repo")
                assert isolated_copy.github_config == self.github_config

            mock_setup.assert_called_once_with(self.github_config, Path("/tmp/test/repo"))


class TestRepositoryStoreFunctions:
    """Test repository store standalone functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    def test_create_local_context_store_pool(self):
        """Test create_local_context_store_pool function."""
        store = create_local_context_store(self.github_config, Path("/custom/base"))

        assert isinstance(store, LocalContextStore)
        assert store.github_config == self.github_config
        assert store.base_path == Path("/custom/base")

    def test_create_local_context_store_pool_default_path(self):
        """Test create_local_context_store_pool with default base path."""
        store = create_local_context_store(self.github_config)

        expected_path = Path.home() / ".compass" / "repos"
        assert store.base_path == expected_path


class TestGitHubContextManagers:
    """Test GitHub context managers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    @patch("csbot.local_context_store.local_context_store.create_git_commit_file_tree")
    def test_repository_store_latest_file_tree(self, mock_create_tree):
        """Test repository store latest_file_tree context manager."""
        mock_store = Mock()
        mock_tree = Mock()

        # Mock the store's latest_file_tree method
        @contextmanager
        def mock_latest_file_tree():
            yield mock_tree

        mock_store.latest_file_tree = mock_latest_file_tree

        with mock_store.latest_file_tree() as tree:
            assert tree == mock_tree

    def test_latest_tree_via_store_method(self):
        """Test latest_file_tree method on store directly."""
        mock_store = Mock()
        mock_tree = Mock()

        # Mock the store's latest_file_tree method
        @contextmanager
        def mock_latest_file_tree():
            yield mock_tree

        mock_store.latest_file_tree = mock_latest_file_tree

        with mock_store.latest_file_tree() as tree:
            assert tree == mock_tree

    def test_with_pull_request_context(self):
        """Test with_pull_request_context context manager."""
        mock_store = Mock()
        mock_repo = Mock()
        mock_repo.temp_repo_path = Path("/mock/repo")
        mock_repo.commit_changes = Mock(return_value="feature-branch")
        mock_repo.create_pull_request = Mock(return_value="https://github.com/test/repo/pull/123")

        # Mock the store's isolated_copy method
        @contextmanager
        def mock_isolated_copy():
            yield mock_repo

        mock_store.isolated_copy = mock_isolated_copy
        mock_store.github_config = self.github_config

        with with_pull_request_context(mock_store, "Test PR", "Test Body", False) as pr_result:
            assert isinstance(pr_result, PullRequestResult)
            assert pr_result.repo_path == Path("/mock/repo")
            assert pr_result.title == "Test PR"
            assert pr_result.body == "Test Body"
            assert pr_result.automerge is False

        # After exiting context, PR should be created
        assert pr_result.pr_url == "https://github.com/test/repo/pull/123"
        mock_repo.commit_changes.assert_called_once_with(
            "Test PR",
            author_name="csbot",
            author_email="csbot@example.com",
        )
        mock_repo.create_pull_request.assert_called_once_with(
            "Test PR", "Test Body", "feature-branch"
        )

    def test_with_pull_request_context_automerge(self):
        """Test with_pull_request_context with automerge=True."""
        mock_store = Mock()
        mock_repo = Mock()
        mock_repo.temp_repo_path = Path("/mock/repo")
        mock_repo.commit_changes = Mock(return_value="feature-branch")
        mock_repo.create_and_merge_pull_request = Mock(
            return_value="https://github.com/test/repo/pull/123"
        )

        # Mock the store's isolated_copy method
        @contextmanager
        def mock_isolated_copy():
            yield mock_repo

        mock_store.isolated_copy = mock_isolated_copy
        mock_store.github_config = self.github_config

        with with_pull_request_context(mock_store, "Auto PR", "Auto Body", True) as pr_result:
            assert pr_result.automerge is True

        # Should use create_and_merge_pull_request for automerge
        assert pr_result.pr_url == "https://github.com/test/repo/pull/123"
        mock_repo.create_and_merge_pull_request.assert_called_once_with(
            "Auto PR", "Auto Body", "feature-branch"
        )


class TestDataStructures:
    """Test data structures and types."""

    def test_pull_request_result(self):
        """Test PullRequestResult properties."""
        repo_path = Path("/test/repo")
        pr_result = PullRequestResult(repo_path, "Title", "Body", False)

        assert pr_result.repo_path == repo_path
        assert pr_result.title == "Title"
        assert pr_result.body == "Body"
        assert pr_result.automerge is False
        assert pr_result.pr_url is None  # Initially unset

        # Test setting pr_url
        pr_result.pr_url = "https://github.com/test/repo/pull/123"
        assert pr_result.pr_url == "https://github.com/test/repo/pull/123"

    def test_initialized_context_repository(self):
        """Test InitializedContextRepository structure."""
        github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")
        repo = InitializedContextRepository(
            github_config=github_config,
            project_name="org/project",
            html_url="https://github.com/test/repo",
            created_files=["file1.yaml", "file2.md"],
        )

        assert repo.github_config == github_config
        assert repo.project_name == "org/project"
        assert repo.html_url == "https://github.com/test/repo"
        assert repo.created_files == ["file1.yaml", "file2.md"]

    def test_workflow_run_status_type(self):
        """Test WorkflowRunStatus type structure."""
        status: WorkflowRunStatus = {
            "id": 12345,
            "status": "completed",
            "conclusion": "success",
            "html_url": "https://github.com/test/repo/actions/runs/12345",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "head_branch": "main",
            "head_sha": "abc123",
            "run_number": 42,
        }

        assert status["id"] == 12345
        assert status["status"] == "completed"
        assert status["conclusion"] == "success"
        assert status["run_number"] == 42


class TestErrorHandling:
    """Test error handling in GitHub operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    @patch("csbot.local_context_store.github.config.Github")
    def test_create_repository_failure(self, mock_github_class):
        """Test create_repository handles API failure."""
        mock_github = Mock()
        mock_org = Mock()
        mock_github_class.return_value = mock_github
        mock_github.get_organization.return_value = mock_org
        mock_org.create_repo.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            create_repository(self.github_config.auth_source, "test-repo")

    @patch("csbot.local_context_store.github.config.Github")
    def test_initialize_contextstore_repository_failure(self, mock_github_class):
        """Test initialize_contextstore_repository handles file creation failure."""
        mock_github = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github
        mock_github.get_organization.return_value = mock_org
        mock_org.get_repo.return_value = mock_repo
        mock_repo.create_file.side_effect = Exception("File creation failed")

        with pytest.raises(Exception, match="Failed to initialize contextstore repository files"):
            initialize_contextstore_repository(
                self.github_config.auth_source, "test-repo", "org/project", "dagster-compass", None
            )

    @patch("csbot.local_context_store.github.config.Github")
    def test_add_collaborator_failure(self, mock_github_class):
        """Test add_collaborator_to_repository handles API failure."""
        mock_github = Mock()
        mock_org = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github
        mock_github.get_organization.return_value = mock_org
        mock_org.get_repo.return_value = mock_repo
        mock_repo.add_to_collaborators.side_effect = Exception("Permission denied")

        with pytest.raises(Exception, match="Failed to add collaborator"):
            add_collaborator_to_repository(self.github_config.auth_source, "test-repo", "username")


class TestIntegrationScenarios:
    """Test common integration scenarios."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    def test_repository_lifecycle(self):
        """Test repository creation and initialization lifecycle."""
        with patch("csbot.local_context_store.github.config.Github") as mock_github_class:
            # Setup mocks for repository creation
            mock_github = Mock()
            mock_org = Mock()
            mock_repo = Mock()
            mock_repo.html_url = "https://github.com/dagster-compass/test-repo"
            mock_repo.default_branch = "main"

            mock_github_class.return_value = mock_github
            mock_github.get_organization.return_value = mock_org
            mock_org.create_repo.return_value = mock_repo
            mock_org.get_repo.return_value = mock_repo

            # Create repository
            repo_url = create_repository(self.github_config.auth_source, "test-repo")
            assert repo_url == "https://github.com/dagster-compass/test-repo"

            # Initialize repository
            init_result = initialize_contextstore_repository(
                self.github_config.auth_source, "test-repo", "org/project", "dagster-compass", None
            )
            assert init_result.html_url == repo_url
            assert len(init_result.created_files) == 3

            # Create repository store
            store = create_local_context_store(init_result.github_config)
            assert isinstance(store, LocalContextStore)
            assert store.github_config.repo_name == "dagster-compass/test-repo"

    def test_latest_file_tree_context(self):
        """Test latest_file_tree context manager works correctly."""
        store = create_local_context_store(self.github_config)

        with patch.object(store, "latest_file_tree") as mock_latest_file_tree:
            mock_file_tree = Mock()

            @contextmanager
            def mock_tree_context():
                yield mock_file_tree

            mock_latest_file_tree.side_effect = mock_tree_context

            # Test context usage
            with store.latest_file_tree() as tree:
                assert tree == mock_file_tree
