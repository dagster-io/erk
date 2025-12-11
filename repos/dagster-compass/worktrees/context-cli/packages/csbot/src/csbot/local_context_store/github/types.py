"""Type definitions for GitHub integration.

This module contains all the data structures, protocols, and type definitions
used throughout the GitHub integration package.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from csbot.local_context_store.github.config import GithubConfig


@dataclass(frozen=True)
class InitializedContextRepository:
    """Represents a successfully initialized context repository.

    Contains all information about the repository that was initialized,
    including configuration needed to work with it.
    """

    github_config: "GithubConfig"
    """GitHub configuration for working with this repository"""

    project_name: str
    """Name of the contextstore project (format: 'org/project')"""

    html_url: str
    """HTML URL of the repository on GitHub"""

    created_files: list[str]
    """List of files that were created during initialization"""


class PullRequestResult:
    """Result of a pull request operation."""

    def __init__(self, repo_path: Path, title: str, body: str, automerge: bool):
        self.repo_path = repo_path
        self.title = title
        self.body = body
        self.automerge = automerge
        self.pr_url: str | None = None


class WorkflowRunStatus(TypedDict):
    """Status information for a GitHub Actions workflow run."""

    id: int
    status: str
    conclusion: str | None
    html_url: str
    created_at: str | None
    updated_at: str | None
    head_branch: str
    head_sha: str
    run_number: int
