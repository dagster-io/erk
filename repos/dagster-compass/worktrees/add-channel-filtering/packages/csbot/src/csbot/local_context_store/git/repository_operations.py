from __future__ import annotations

import os
from datetime import datetime
from shutil import rmtree
from typing import TYPE_CHECKING

import backoff
import pygit2
from ddtrace.trace import tracer

from csbot.utils.check_async_context import ensure_not_in_async_context

if TYPE_CHECKING:
    from pathlib import Path

    from csbot.local_context_store.github.config import GithubConfig


SHALLOW_CLONE_DEPTH = 1


def commit_and_push_changes(
    local_repo_path: Path,
    title: str,
    *,
    github_config: GithubConfig,
    author_name: str,
    author_email: str,
) -> str:
    """
    Complete workflow: create branch, stage changes, commit, and push.

    Args:
        local_repo_path: Path to the local git repository
        title: Commit message
        github_config: GitHub configuration for authentication
        author_name: Author name for the commit
        author_email: Author email for the commit

    Returns:
        str: The branch name that was created and pushed
    """
    ensure_not_in_async_context()
    branch_name = _generate_unique_branch_name()
    _create_and_checkout_branch(local_repo_path, branch_name)
    _stage_all_changes(local_repo_path)
    _create_commit(local_repo_path, title, author_name, author_email)
    _push_branch(local_repo_path, branch_name, github_config=github_config)
    return branch_name


def clean_and_update_repository(local_repo_path: Path, *, github_config: GithubConfig) -> None:
    """
    Clean untracked files, fetch from remote, and reset to origin branch using GitConfig.

    Args:
        local_repo_path: Path to the local git repository
        git_config: Git configuration for authentication
    """
    ensure_not_in_async_context()
    _clean_working_directory(local_repo_path)
    _fetch_repository_and_repoint_origin(local_repo_path, github_config=github_config)
    branch_name = _get_default_branch_name(local_repo_path)
    _reset_to_remote_branch(local_repo_path, branch_name)


def _get_default_branch_name(local_repo_path: Path) -> str:
    """
    Get the name of the default branch (main or master).

    Args:
        local_repo_path: Path to the git repository

    Returns:
        str: Name of the default branch ("main" or "master")

    Raises:
        ValueError: If neither main nor master branch exists
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))

    try:
        repo.lookup_reference("refs/remotes/origin/main")
        return "main"
    except KeyError:
        try:
            repo.lookup_reference("refs/remotes/origin/master")
            return "master"
        except KeyError:
            raise ValueError("Could not find origin/main or origin/master branch")


def _reset_to_remote_branch(local_repo_path: Path, branch_name: str) -> None:
    """
    Reset the repository to match the remote branch.

    Args:
        local_repo_path: Path to the git repository
        branch_name: Name of the branch to reset to
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))
    remote_branch = repo.lookup_reference(f"refs/remotes/origin/{branch_name}")

    if remote_branch:
        repo.reset(remote_branch.target, pygit2.enums.ResetMode.HARD)  # type: ignore
        repo.set_head(f"refs/heads/{branch_name}")
    else:
        raise ValueError(f"Could not find origin/{branch_name} branch")


def _clean_working_directory(local_repo_path: Path) -> None:
    """
    Clean all untracked files and directories from the working directory.

    Args:
        local_repo_path: Path to the git repository
    """
    ensure_not_in_async_context()
    for file in os.listdir(local_repo_path):
        full_path = local_repo_path / file
        if file == ".git":
            continue
        if full_path.is_file():
            full_path.unlink(missing_ok=True)
        elif full_path.is_dir():
            rmtree(full_path, ignore_errors=True)


def _create_and_checkout_branch(local_repo_path: Path, branch_name: str) -> None:
    """
    Create a new branch from current HEAD and check it out.

    Args:
        local_repo_path: Path to the git repository
        branch_name: Name of the new branch
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))
    head = repo.head
    commit = repo.get(head.target)  # type: ignore

    if not isinstance(commit, pygit2.Commit):
        raise ValueError("Could not get commit object")

    repo.create_branch(branch_name, commit)
    branch_ref = f"refs/heads/{branch_name}"
    repo.set_head(branch_ref)


def _stage_all_changes(local_repo_path: Path) -> None:
    """
    Stage all changes in the working directory.

    Args:
        local_repo_path: Path to the git repository
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))
    repo.index.add_all()
    repo.index.write()


def _create_commit(
    local_repo_path: Path,
    title: str,
    author_name: str = "csbot",
    author_email: str = "csbot@example.com",
) -> str:
    """
    Create a commit with staged changes.

    Args:
        local_repo_path: Path to the git repository
        title: Commit message
        author_name: Author name for the commit
        author_email: Author email for the commit

    Returns:
        str: The commit hash
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))
    head = repo.head

    tree = repo.index.write_tree()
    author = pygit2.Signature(author_name, author_email)
    committer = author

    commit_id = repo.create_commit(head.name, author, committer, title, tree, [head.target])
    return str(commit_id)


@backoff.on_exception(backoff.expo, pygit2.GitError, max_tries=3, max_time=30)
@tracer.wrap("git.push_branch")
def _push_branch(local_repo_path: Path, branch_name: str, *, github_config: GithubConfig) -> None:
    """
    Push a branch to remote origin using GitHub configuration.

    Args:
        local_repo_path: Path to the local git repository
        branch_name: Name of the branch to push
        github_config: GitHub configuration for authentication
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))
    remote = repo.remotes["origin"]
    branch_ref = f"refs/heads/{branch_name}"

    with tracer.trace("git.push", resource=branch_ref):
        remote.push([branch_ref], callbacks=github_config.auth_source.get_callbacks_sync())


def _generate_unique_branch_name() -> str:
    """
    Generate a unique branch name with timestamp.

    Returns:
        str: Unique branch name in format "csbot_YYYYMMDD_HHMMSS"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"csbot_{timestamp}"


@backoff.on_exception(backoff.expo, pygit2.GitError, max_tries=3, max_time=30)
@tracer.wrap("git.clone_repository")
def clone_repository(local_path: Path, *, git_config: GithubConfig, depth: int) -> None:
    """
    Clone a Git repository using GitConfig with embedded authentication.

    Args:
        local_path: Local path where repository should be cloned
        git_config: Git configuration containing repo URL with authentication
        depth: Depth of clone (default: 1 for shallow clone)
    """
    ensure_not_in_async_context()

    with tracer.trace("git.clone_repository", resource=git_config.base_repo_url()):
        pygit2.clone_repository(
            git_config.base_repo_url(),
            str(local_path),
            depth=depth,
            callbacks=git_config.auth_source.get_callbacks_sync(),
        )


@backoff.on_exception(backoff.expo, pygit2.GitError, max_tries=3, max_time=30)
@tracer.wrap("git.fetch_repository")
def _fetch_repository(local_repo_path: Path, *, github_config: GithubConfig) -> None:
    """
    Fetch latest changes from remote origin using GitHub configuration.

    Args:
        local_repo_path: Path to the local git repository
        github_config: GitHub configuration for authentication
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))
    remote = repo.remotes["origin"]
    with tracer.trace("git.fetch"):
        remote.fetch(callbacks=github_config.auth_source.get_callbacks_sync())


@backoff.on_exception(backoff.expo, pygit2.GitError, max_tries=3, max_time=30)
@tracer.wrap("git.fetch_repository_and_repoint_origin")
def _fetch_repository_and_repoint_origin(
    local_repo_path: Path, *, github_config: GithubConfig
) -> None:
    """
    Fetch latest changes from remote origin using GithubConfig.

    Also, repoint origin to the new remote that is in the GithubConfig.

    Args:
        local_repo_path: Path to the local git repository
        git_config: Git configuration for authentication
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(local_repo_path))

    repo.remotes.delete("origin")
    remote = repo.remotes.create("origin", github_config.base_repo_url())
    with tracer.trace("git.fetch"):
        remote.fetch(callbacks=github_config.auth_source.get_callbacks_sync())
