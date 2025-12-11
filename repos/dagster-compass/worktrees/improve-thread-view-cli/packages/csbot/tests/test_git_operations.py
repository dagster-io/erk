from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pygit2
import pytest

from csbot.local_context_store.git.repository_operations import (
    _clean_working_directory,
    _create_and_checkout_branch,
    _create_commit,
    _fetch_repository,
    _generate_unique_branch_name,
    _get_default_branch_name,
    _push_branch,
    _reset_to_remote_branch,
    _stage_all_changes,
    clean_and_update_repository,
    commit_and_push_changes,
)
from csbot.local_context_store.github.config import GithubConfig


@pytest.fixture
def mock_github_config():
    """Create a mock GitHubConfig for testing."""
    return GithubConfig.pat(token="test-token", repo_name="owner/repo")


class TestFetchRepository:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test_fetch_repository_success(self, mock_repo_class, mock_github_config):
        repo_path = Path("/tmp/repo")
        mock_repo = Mock()
        mock_remote = Mock()
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo_class.return_value = mock_repo

        _fetch_repository(repo_path, github_config=mock_github_config)

        mock_repo_class.assert_called_once_with(str(repo_path))
        mock_remote.fetch.assert_called_once()

    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test_fetch_repository_no_origin(self, mock_repo_class, mock_github_config):
        repo_path = Path("/tmp/repo")
        mock_repo = Mock()
        mock_repo.remotes = {}
        mock_repo_class.return_value = mock_repo

        with pytest.raises(KeyError):
            _fetch_repository(repo_path, github_config=mock_github_config)


class TestGetDefaultBranchName:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test_get_default_branch_main_exists(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        mock_repo = Mock()
        mock_repo.lookup_reference.return_value = Mock()  # main branch exists
        mock_repo_class.return_value = mock_repo

        branch_name = _get_default_branch_name(repo_path)

        assert branch_name == "main"
        mock_repo.lookup_reference.assert_called_once_with("refs/remotes/origin/main")

    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test_get_default_branch_falls_back_to_master(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        mock_repo = Mock()
        mock_repo.lookup_reference.side_effect = [KeyError(), Mock()]  # main fails, master succeeds
        mock_repo_class.return_value = mock_repo

        branch_name = _get_default_branch_name(repo_path)

        assert branch_name == "master"
        assert mock_repo.lookup_reference.call_count == 2

    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test_get_default_branch_neither_exists(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        mock_repo = Mock()
        mock_repo.lookup_reference.side_effect = [KeyError(), KeyError()]  # both fail
        mock_repo_class.return_value = mock_repo

        with pytest.raises(ValueError, match="Could not find origin/main or origin/master branch"):
            _get_default_branch_name(repo_path)


class TestResetToRemoteBranch:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test__reset_to_remote_branch_success(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        branch_name = "main"
        mock_repo = Mock()
        mock_remote_branch = Mock()
        mock_remote_branch.target = "commit_hash"
        mock_repo.lookup_reference.return_value = mock_remote_branch
        mock_repo_class.return_value = mock_repo

        _reset_to_remote_branch(repo_path, branch_name)

        mock_repo.lookup_reference.assert_called_once_with(f"refs/remotes/origin/{branch_name}")
        mock_repo.reset.assert_called_once_with("commit_hash", pygit2.enums.ResetMode.HARD)
        mock_repo.set_head.assert_called_once_with(f"refs/heads/{branch_name}")

    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test__reset_to_remote_branch_not_found(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        branch_name = "nonexistent"
        mock_repo = Mock()
        mock_repo.lookup_reference.return_value = None
        mock_repo_class.return_value = mock_repo

        with pytest.raises(ValueError, match=f"Could not find origin/{branch_name} branch"):
            _reset_to_remote_branch(repo_path, branch_name)


class TestCleanWorkingDirectory:
    def test__clean_working_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create some test files and directories
            (repo_path / "file1.txt").write_text("content1")
            (repo_path / "file2.txt").write_text("content2")
            (repo_path / "subdir").mkdir()
            (repo_path / "subdir" / "file3.txt").write_text("content3")

            # Create .git directory (should be preserved)
            git_dir = repo_path / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("git config")

            _clean_working_directory(repo_path)

            # Check that .git is preserved
            assert git_dir.exists()
            assert (git_dir / "config").exists()

            # Check that other files/dirs are removed
            assert not (repo_path / "file1.txt").exists()
            assert not (repo_path / "file2.txt").exists()
            assert not (repo_path / "subdir").exists()


class TestCleanAndUpdateRepository:
    @patch("csbot.local_context_store.git.repository_operations._clean_working_directory")
    @patch(
        "csbot.local_context_store.git.repository_operations._fetch_repository_and_repoint_origin"
    )
    @patch("csbot.local_context_store.git.repository_operations._get_default_branch_name")
    @patch("csbot.local_context_store.git.repository_operations._reset_to_remote_branch")
    def test_clean_and_update_repository(
        self, mock_reset, mock_get_branch, mock_fetch, mock_clean, mock_github_config
    ):
        repo_path = Path("/tmp/repo")
        mock_get_branch.return_value = "main"

        clean_and_update_repository(repo_path, github_config=mock_github_config)

        mock_clean.assert_called_once_with(repo_path)
        mock_fetch.assert_called_once_with(repo_path, github_config=mock_github_config)
        mock_get_branch.assert_called_once_with(repo_path)
        mock_reset.assert_called_once_with(repo_path, "main")


class TestCreateAndCheckoutBranch:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test__create_and_checkout_branch_success(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        branch_name = "feature-branch"

        mock_repo = Mock()
        mock_head = Mock()
        mock_head.target = "commit_hash"
        mock_repo.head = mock_head

        mock_commit = Mock(spec=pygit2.Commit)
        mock_repo.get.return_value = mock_commit
        mock_repo_class.return_value = mock_repo

        _create_and_checkout_branch(repo_path, branch_name)

        mock_repo.get.assert_called_once_with("commit_hash")
        mock_repo.create_branch.assert_called_once_with(branch_name, mock_commit)
        mock_repo.set_head.assert_called_once_with(f"refs/heads/{branch_name}")

    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test__create_and_checkout_branch_invalid_commit(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        branch_name = "feature-branch"

        mock_repo = Mock()
        mock_head = Mock()
        mock_head.target = "commit_hash"
        mock_repo.head = mock_head
        mock_repo.get.return_value = "not_a_commit"  # Invalid commit type
        mock_repo_class.return_value = mock_repo

        with pytest.raises(ValueError, match="Could not get commit object"):
            _create_and_checkout_branch(repo_path, branch_name)


class TestStageAllChanges:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test__stage_all_changes(self, mock_repo_class):
        repo_path = Path("/tmp/repo")
        mock_repo = Mock()
        mock_index = Mock()
        mock_repo.index = mock_index
        mock_repo_class.return_value = mock_repo

        _stage_all_changes(repo_path)

        mock_index.add_all.assert_called_once()
        mock_index.write.assert_called_once()


class TestCreateCommit:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Signature")
    def test__create_commit_default_author(self, mock_signature, mock_repo_class):
        repo_path = Path("/tmp/repo")
        title = "Test commit"

        mock_repo = Mock()
        mock_head = Mock()
        mock_head.name = "refs/heads/main"
        mock_head.target = "parent_commit_hash"
        mock_repo.head = mock_head
        mock_index = Mock()
        mock_index.write_tree.return_value = "tree_hash"
        mock_repo.index = mock_index
        mock_repo.create_commit.return_value = "new_commit_hash"
        mock_repo_class.return_value = mock_repo

        mock_author = Mock()
        mock_signature.return_value = mock_author

        commit_hash = _create_commit(repo_path, title)

        assert commit_hash == "new_commit_hash"
        mock_signature.assert_called_once_with("csbot", "csbot@example.com")
        mock_repo.create_commit.assert_called_once_with(
            "refs/heads/main", mock_author, mock_author, title, "tree_hash", ["parent_commit_hash"]
        )

    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Signature")
    def test__create_commit_custom_author(self, mock_signature, mock_repo_class):
        repo_path = Path("/tmp/repo")
        title = "Test commit"
        author_name = "Custom Author"
        author_email = "custom@example.com"

        mock_repo = Mock()
        mock_head = Mock()
        mock_head.name = "refs/heads/main"
        mock_head.target = "parent_commit_hash"
        mock_repo.head = mock_head
        mock_index = Mock()
        mock_index.write_tree.return_value = "tree_hash"
        mock_repo.index = mock_index
        mock_repo.create_commit.return_value = "new_commit_hash"
        mock_repo_class.return_value = mock_repo

        mock_author = Mock()
        mock_signature.return_value = mock_author

        _create_commit(repo_path, title, author_name, author_email)

        mock_signature.assert_called_once_with(author_name, author_email)


class TestPushBranch:
    @patch("csbot.local_context_store.git.repository_operations.pygit2.Repository")
    def test__push_branch(self, mock_repo_class, mock_github_config):
        repo_path = Path("/tmp/repo")
        branch_name = "feature-branch"

        mock_repo = Mock()
        mock_remote = Mock()
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo_class.return_value = mock_repo

        _push_branch(repo_path, branch_name, github_config=mock_github_config)

        mock_remote.push.assert_called_once_with(
            [f"refs/heads/{branch_name}"], callbacks=mock_remote.push.call_args[1]["callbacks"]
        )


class TestGenerateUniqueBranchName:
    @patch("csbot.local_context_store.git.repository_operations.datetime")
    def test__generate_unique_branch_name(self, mock_datetime):
        mock_now = Mock()
        mock_now.strftime.return_value = "20240101_120000"
        mock_datetime.now.return_value = mock_now

        branch_name = _generate_unique_branch_name()

        assert branch_name == "csbot_20240101_120000"
        mock_now.strftime.assert_called_once_with("%Y%m%d_%H%M%S")


class TestCommitAndPushChanges:
    @patch("csbot.local_context_store.git.repository_operations._generate_unique_branch_name")
    @patch("csbot.local_context_store.git.repository_operations._create_and_checkout_branch")
    @patch("csbot.local_context_store.git.repository_operations._stage_all_changes")
    @patch("csbot.local_context_store.git.repository_operations._create_commit")
    @patch("csbot.local_context_store.git.repository_operations._push_branch")
    def test_commit_and_push_changes_default_author(
        self,
        mock_push,
        mock_commit,
        mock_stage,
        mock_checkout,
        mock_generate_branch,
        mock_github_config,
    ):
        repo_path = Path("/tmp/repo")
        title = "Test commit"
        branch_name = "csbot_20240101_120000"

        mock_generate_branch.return_value = branch_name

        result = commit_and_push_changes(
            repo_path,
            title,
            github_config=mock_github_config,
            author_name="csbot",
            author_email="csbot@example.com",
        )

        assert result == branch_name
        mock_generate_branch.assert_called_once()
        mock_checkout.assert_called_once_with(repo_path, branch_name)
        mock_stage.assert_called_once_with(repo_path)
        mock_commit.assert_called_once_with(repo_path, title, "csbot", "csbot@example.com")
        mock_push.assert_called_once_with(repo_path, branch_name, github_config=mock_github_config)

    @patch("csbot.local_context_store.git.repository_operations._generate_unique_branch_name")
    @patch("csbot.local_context_store.git.repository_operations._create_and_checkout_branch")
    @patch("csbot.local_context_store.git.repository_operations._stage_all_changes")
    @patch("csbot.local_context_store.git.repository_operations._create_commit")
    @patch("csbot.local_context_store.git.repository_operations._push_branch")
    def test_commit_and_push_changes_custom_author(
        self,
        mock_push,
        mock_commit,
        mock_stage,
        mock_checkout,
        mock_generate_branch,
        mock_github_config,
    ):
        repo_path = Path("/tmp/repo")
        title = "Test commit"
        author_name = "Custom Author"
        author_email = "custom@example.com"
        branch_name = "csbot_20240101_120000"

        mock_generate_branch.return_value = branch_name

        result = commit_and_push_changes(
            repo_path,
            title,
            github_config=mock_github_config,
            author_name=author_name,
            author_email=author_email,
        )

        assert result == branch_name
        mock_commit.assert_called_once_with(repo_path, title, author_name, author_email)
        mock_push.assert_called_once_with(repo_path, branch_name, github_config=mock_github_config)


class TestIntegration:
    """Integration tests that use real file system operations (but mock git operations)."""

    def test__clean_working_directory_with_real_filesystem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Set up test files and directories
            test_file = repo_path / "test_file.txt"
            test_file.write_text("test content")

            test_dir = repo_path / "test_dir"
            test_dir.mkdir()
            (test_dir / "nested_file.txt").write_text("nested content")

            git_dir = repo_path / ".git"
            git_dir.mkdir()
            git_config = git_dir / "config"
            git_config.write_text("git config content")

            # Verify setup
            assert test_file.exists()
            assert test_dir.exists()
            assert git_config.exists()

            # Clean the directory
            _clean_working_directory(repo_path)

            # Verify results
            assert not test_file.exists()
            assert not test_dir.exists()
            assert git_config.exists()  # .git should be preserved
