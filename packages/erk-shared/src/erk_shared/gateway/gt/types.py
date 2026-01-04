"""Type definitions for GT kit operations."""

from dataclasses import dataclass
from typing import Literal, NamedTuple


class CommandResult(NamedTuple):
    """Result from running a subprocess command.

    Attributes:
        success: True if command exited with code 0, False otherwise
        stdout: Standard output from the command
        stderr: Standard error from the command
    """

    success: bool
    stdout: str
    stderr: str


# =============================================================================
# Squash Operation Types
# =============================================================================


@dataclass(frozen=True)
class SquashSuccess:
    """Success result from idempotent squash."""

    success: Literal[True]
    action: Literal["squashed", "already-single-commit"]
    commit_count: int
    message: str


@dataclass(frozen=True)
class SquashError:
    """Error result from idempotent squash."""

    success: Literal[False]
    error: Literal["no-commits", "squash-conflict", "squash-failed"]
    message: str


# =============================================================================
# Update PR Operation Types
# =============================================================================

# Update PR uses dict[str, Any] for flexibility, no specific dataclasses needed


# =============================================================================
# Land PR Operation Types
# =============================================================================

LandPrErrorType = Literal[
    "parent-not-trunk",
    "no-pr-found",
    "pr-not-open",
    "pr-base-mismatch",
    "github-api-error",
    "merge-failed",
]


@dataclass(frozen=True)
class LandPrSuccess:
    """Success result from landing a PR."""

    success: bool
    pr_number: int
    branch_name: str
    message: str


@dataclass(frozen=True)
class LandPrError:
    """Error result from landing a PR."""

    success: bool
    error_type: LandPrErrorType
    message: str
    details: dict[str, str | int | list[str]]


# =============================================================================
# Prep Operation Types
# =============================================================================

PrepErrorType = Literal[
    "gt-not-authenticated",
    "gh-not-authenticated",
    "no-branch",
    "no-parent",
    "no-commits",
    "restack-conflict",
    "squash-conflict",
    "squash-failed",
]


@dataclass(frozen=True)
class PrepResult:
    """Success result from prep phase."""

    success: bool
    diff_file: str
    repo_root: str
    current_branch: str
    parent_branch: str
    commit_count: int
    squashed: bool
    message: str


@dataclass(frozen=True)
class PrepError:
    """Error result from prep phase."""

    success: bool
    error_type: PrepErrorType
    message: str
    details: dict[str, str | bool]


# =============================================================================
# Submit Branch Operation Types
# =============================================================================

PreAnalysisErrorType = Literal[
    "gt-not-authenticated",
    "gh-not-authenticated",
    "no-branch",
    "no-parent",
    "no-commits",
    "squash-failed",
    "squash-conflict",
    "parent-merged",
]

PostAnalysisErrorType = Literal[
    "amend-failed",
    "submit-failed",
    "submit-timeout",
    "submit-merged-parent",
    "submit-diverged",
    "submit-conflict",
    "submit-empty-parent",
    "pr-update-failed",
    "claude-not-available",
    "ai-generation-failed",
]


@dataclass(frozen=True)
class PreAnalysisResult:
    """Success result from pre-analysis phase."""

    success: bool
    branch_name: str
    parent_branch: str
    commit_count: int
    squashed: bool
    uncommitted_changes_committed: bool
    message: str
    has_conflicts: bool = False
    conflict_details: dict[str, str] | None = None
    commit_messages: list[str] | None = None  # Full commit messages for AI context
    issue_number: int | None = None  # Issue number if linked via .impl/issue.json


@dataclass(frozen=True)
class PreAnalysisError:
    """Error result from pre-analysis phase."""

    success: bool
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, str | bool]


@dataclass(frozen=True)
class PostAnalysisResult:
    """Success result from post-analysis phase."""

    success: bool
    pr_number: int | None
    pr_url: str
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str


@dataclass(frozen=True)
class PostAnalysisError:
    """Error result from post-analysis phase."""

    success: bool
    error_type: PostAnalysisErrorType
    message: str
    details: dict[str, str]


@dataclass(frozen=True)
class PreflightResult:
    """Result from preflight phase (pre-analysis + submit + diff extraction)."""

    success: bool
    pr_number: int
    pr_url: str
    graphite_url: str
    branch_name: str
    diff_file: str  # Path to temp diff file
    repo_root: str
    current_branch: str
    parent_branch: str
    issue_number: int | None
    message: str
    commit_messages: list[str] | None = None  # Full commit messages for AI context


@dataclass
class FinalizeResult:
    """Result from finalize phase (update PR metadata)."""

    success: bool
    pr_number: int
    pr_url: str
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str


# =============================================================================
# Quick Submit Operation Types
# =============================================================================

QuickSubmitErrorType = Literal["stage-failed", "commit-failed", "submit-failed"]


@dataclass(frozen=True)
class QuickSubmitSuccess:
    """Success result from quick-submit operation."""

    success: Literal[True]
    staged_changes: bool
    committed: bool
    message: str
    pr_url: str | None


@dataclass(frozen=True)
class QuickSubmitError:
    """Error result from quick-submit operation."""

    success: Literal[False]
    error_type: QuickSubmitErrorType
    message: str
