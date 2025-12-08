"""Type definitions for git-only PR operations."""

from dataclasses import dataclass
from typing import Literal

# =============================================================================
# Preflight Operation Types
# =============================================================================

GitPreflightErrorType = Literal[
    "gh_not_authenticated",
    "no_branch",
    "not_in_repo",
    "stage_failed",
    "commit_failed",
    "push_failed",
    "pr_create_failed",
]


@dataclass(frozen=True)
class GitPreflightResult:
    """Success result from git-only preflight phase."""

    success: Literal[True]
    pr_number: int
    pr_url: str
    branch_name: str
    diff_file: str  # Path to temp diff file for AI analysis
    issue_number: int | None
    pr_created: bool  # True if new PR, False if existing PR found
    repo_root: str
    parent_branch: str
    commit_messages: list[str]  # Commit messages for AI context
    message: str


@dataclass(frozen=True)
class GitPreflightError:
    """Error result from git-only preflight phase."""

    success: Literal[False]
    error_type: GitPreflightErrorType
    message: str
    details: dict[str, str]


# =============================================================================
# Finalize Operation Types
# =============================================================================

GitFinalizeErrorType = Literal["pr_update_failed",]


@dataclass(frozen=True)
class GitFinalizeResult:
    """Success result from git-only finalize phase."""

    success: Literal[True]
    pr_number: int
    pr_url: str
    pr_title: str
    branch_name: str
    issue_number: int | None
    message: str


@dataclass(frozen=True)
class GitFinalizeError:
    """Error result from git-only finalize phase."""

    success: Literal[False]
    error_type: GitFinalizeErrorType
    message: str
    details: dict[str, str]
