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


@dataclass
class SquashSuccess:
    """Success result from idempotent squash."""

    success: Literal[True]
    action: Literal["squashed", "already_single_commit"]
    commit_count: int
    message: str


@dataclass
class SquashError:
    """Error result from idempotent squash."""

    success: Literal[False]
    error: Literal["no_commits", "squash_conflict", "squash_failed"]
    message: str


# =============================================================================
# Update PR Operation Types
# =============================================================================

# Update PR uses dict[str, Any] for flexibility, no specific dataclasses needed


# =============================================================================
# Land PR Operation Types
# =============================================================================

LandPrErrorType = Literal[
    "parent_not_trunk",
    "no_pr_found",
    "pr_not_open",
    "pr_base_mismatch",
    "github_api_error",
    "merge_failed",
]


@dataclass
class LandPrSuccess:
    """Success result from landing a PR."""

    success: bool
    pr_number: int
    branch_name: str
    message: str


@dataclass
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
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_parent",
    "no_commits",
    "restack_conflict",
    "squash_conflict",
    "squash_failed",
]


@dataclass
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


@dataclass
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
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_parent",
    "no_commits",
    "squash_failed",
    "squash_conflict",
    "parent_merged",
]

PostAnalysisErrorType = Literal[
    "amend_failed",
    "submit_failed",
    "submit_timeout",
    "submit_merged_parent",
    "submit_diverged",
    "submit_conflict",
    "submit_empty_parent",
    "pr_update_failed",
    "claude_not_available",
    "ai_generation_failed",
]


@dataclass
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


@dataclass
class PreAnalysisError:
    """Error result from pre-analysis phase."""

    success: bool
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, str | bool]


@dataclass
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


@dataclass
class PostAnalysisError:
    """Error result from post-analysis phase."""

    success: bool
    error_type: PostAnalysisErrorType
    message: str
    details: dict[str, str]


@dataclass
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
# Auto-Restack Operation Types
# =============================================================================

RestackPreflightErrorType = Literal[
    "squash_conflict",
    "squash_failed",
    "no_commits",
    "restack_failed",
    "not_in_repo",
    "dirty_working_tree",
]


@dataclass(frozen=True)
class RestackPreflightSuccess:
    """Success result from restack preflight."""

    success: Literal[True]
    has_conflicts: bool
    conflicts: list[str]  # File paths
    branch_name: str
    message: str


@dataclass(frozen=True)
class RestackPreflightError:
    """Error result from restack preflight."""

    success: Literal[False]
    error_type: RestackPreflightErrorType
    message: str
    details: dict[str, str]


RestackContinueErrorType = Literal["stage_failed", "continue_failed"]


@dataclass(frozen=True)
class RestackContinueSuccess:
    """Success result from restack continue."""

    success: Literal[True]
    restack_complete: bool
    has_conflicts: bool
    conflicts: list[str]  # New conflict files
    branch_name: str
    message: str


@dataclass(frozen=True)
class RestackContinueError:
    """Error result from restack continue."""

    success: Literal[False]
    error_type: RestackContinueErrorType
    message: str
    details: dict[str, str]


RestackFinalizeErrorType = Literal[
    "rebase_still_in_progress", "dirty_working_tree", "unresolved_conflicts"
]


@dataclass(frozen=True)
class RestackFinalizeSuccess:
    """Success result from restack finalize."""

    success: Literal[True]
    branch_name: str
    message: str


@dataclass(frozen=True)
class RestackFinalizeError:
    """Error result from restack finalize."""

    success: Literal[False]
    error_type: RestackFinalizeErrorType
    message: str
    details: dict[str, str]


# =============================================================================
# Quick Submit Operation Types
# =============================================================================

QuickSubmitErrorType = Literal["stage_failed", "commit_failed", "submit_failed"]


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
