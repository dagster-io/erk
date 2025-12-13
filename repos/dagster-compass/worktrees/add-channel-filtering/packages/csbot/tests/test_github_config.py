from __future__ import annotations

import pytest

from csbot.local_context_store.github.config import GithubConfig


class TestGitHubConfig:
    def test_valid_config(self):
        config = GithubConfig.pat(token="test_token", repo_name="owner/repo")
        assert config.repo_name == "owner/repo"
        assert config.owner == "owner"
        assert config.repository == "repo"

    def test_empty_token_raises_error(self):
        with pytest.raises(ValueError, match="GitHub token cannot be empty"):
            GithubConfig.pat(token="", repo_name="owner/repo")

    def test_empty_repo_name_raises_error(self):
        with pytest.raises(ValueError, match="Repository name cannot be empty"):
            GithubConfig.pat(token="test_token", repo_name="")

    def test_invalid_repo_format_no_slash(self):
        with pytest.raises(ValueError, match="Repository name must be in format 'owner/repo'"):
            GithubConfig.pat(token="test_token", repo_name="invalid_repo")

    def test_invalid_repo_format_multiple_slashes(self):
        with pytest.raises(ValueError, match="Repository name must be in format 'owner/repo'"):
            GithubConfig.pat(token="test_token", repo_name="owner/repo/extra")

    def test_empty_owner_raises_error(self):
        with pytest.raises(ValueError, match="Both owner and repository name must be non-empty"):
            GithubConfig.pat(token="test_token", repo_name="/repo")

    def test_empty_repository_raises_error(self):
        with pytest.raises(ValueError, match="Both owner and repository name must be non-empty"):
            GithubConfig.pat(token="test_token", repo_name="owner/")

    def test_config_is_immutable(self):
        config = GithubConfig.pat(token="test_token", repo_name="owner/repo")

        # Test that we can't modify the config
        with pytest.raises(AttributeError):
            config.token = "new_token"  # type: ignore[misc]

        with pytest.raises(AttributeError):
            config.repo_name = "new_owner/new_repo"  # type: ignore[misc]
