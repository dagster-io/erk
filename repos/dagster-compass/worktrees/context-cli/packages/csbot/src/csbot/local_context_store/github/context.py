"""Context managers for GitHub repository operations.

This module provides context managers for working with GitHub repositories,
pull requests, and git operations with proper resource management.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from csbot.local_context_store.github.types import PullRequestResult
from csbot.local_context_store.isolated_copy import IsolatedContextStoreCopy
from csbot.local_context_store.local_context_store import setup_fresh_github_repository
from csbot.utils.check_async_context import ensure_not_in_async_context

if TYPE_CHECKING:
    from collections.abc import Generator

    from csbot.local_context_store.github.config import GithubConfig
    from csbot.local_context_store.local_context_store import LocalContextStore


def create_pr_workspace(github_config: "GithubConfig") -> tuple[Path, Path]:
    """Create a temporary workspace for PR operations.

    This creates a temporary directory and clones the repository into it.
    The caller is responsible for cleaning up the temporary directory.

    Args:
        github_config: GitHub configuration

    Returns:
        Tuple of (temp_dir_path, repo_path)
    """
    temp_dir = Path(tempfile.mkdtemp())
    repo_path = temp_dir / "repo"
    setup_fresh_github_repository(github_config, repo_path)
    return temp_dir, repo_path


def commit_and_create_pr(
    repo_path: Path,
    github_config: "GithubConfig",
    title: str,
    body: str,
    automerge: bool,
) -> str:
    """Commit changes and create a pull request.

    Args:
        repo_path: Path to the repository with changes
        github_config: GitHub configuration
        title: Pull request title
        body: Pull request body
        automerge: Whether to automatically merge the pull request

    Returns:
        URL of the created (and optionally merged) pull request
    """
    isolated_copy = IsolatedContextStoreCopy(repo_path, github_config)

    # Commit and push changes
    branch_name = isolated_copy.commit_changes(
        title,
        author_name="csbot",
        author_email="csbot@example.com",
    )

    # Create (and optionally merge) the pull request
    if automerge:
        return isolated_copy.create_and_merge_pull_request(title, body, branch_name)
    else:
        return isolated_copy.create_pull_request(title, body, branch_name)


@contextmanager
def with_pull_request_context(
    local_context_store: "LocalContextStore",
    title: str,
    body: str,
    automerge: bool,
) -> "Generator[PullRequestResult]":
    """
    Context manager that creates a pull request with proper resource management.

    Args:
        local_context_store: Local context store pool for performance optimization (contains GitHub config)
        title: Pull request title
        body: Pull request body
        automerge: Whether to automatically merge the pull request

    Yields:
        PullRequestResult: Result object with repo_path and pr_url

    Example:
        from csbot.local_context_store.local_context_store import RepoConfig, SharedRepo
        repo_config = RepoConfig(github_config=github_config, base_path=base_path)
        local_context_store = LocalContextStore(SharedRepo(repo_config=repo_config))
        with with_pull_request_context(local_context_store, title, body, automerge) as pr:
            # Make changes to files in pr.repo_path
            (pr.repo_path / "file.txt").write_text("content")
            # PR is automatically created and committed on exit
    """

    ensure_not_in_async_context()

    # Use isolated_copy to get isolated repo for PR workflow
    with local_context_store.isolated_copy() as isolated_cs_copy:
        result = PullRequestResult(isolated_cs_copy.temp_repo_path, title, body, automerge)

        yield result
        # Commit and push changes using repository interface
        branch_name = isolated_cs_copy.commit_changes(
            title,
            author_name="csbot",
            author_email="csbot@example.com",
        )

        if automerge:
            result.pr_url = isolated_cs_copy.create_and_merge_pull_request(title, body, branch_name)
        else:
            result.pr_url = isolated_cs_copy.create_pull_request(title, body, branch_name)
