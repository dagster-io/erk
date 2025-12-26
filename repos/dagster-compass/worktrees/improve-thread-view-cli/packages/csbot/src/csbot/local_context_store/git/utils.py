"""Utility functions for git operations.

This module contains helper functions and utilities used throughout
the git integration package.
"""

from pathlib import Path

import pygit2

from csbot.contextengine.contextstore_protocol import GitCommitInfo, GitInfo


def extract_git_info(local_repo_path: Path, repository_name: str) -> GitInfo:
    """
    Extract git information from a repository.

    Args:
        local_repo_path: Path to the local git repository
        repository_name: Name/identifier for the repository

    Returns:
        GitInfo: Information about the git repository and current commit
    """
    repo = pygit2.Repository(str(local_repo_path))
    commit_obj = repo[repo.head.target]
    commit = commit_obj.peel(pygit2.Commit)

    return GitInfo(
        repository=repository_name,
        branch=repo.head.name,
        last_commit=GitCommitInfo(
            hash=str(commit.id),
            author=commit.author.name,
            email=commit.author.email,
            message=commit.message,
            time=commit.commit_time,
        ),
    )
