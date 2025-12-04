"""Type definitions for GT kit operations."""

from typing import Literal, NamedTuple, NotRequired, TypedDict


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


class SquashSuccess(TypedDict):
    """Success result from idempotent squash."""

    success: Literal[True]
    action: Literal["squashed", "already_single_commit"]
    commit_count: int
    message: str


class SquashError(TypedDict):
    """Error result from idempotent squash."""

    success: Literal[False]
    error: Literal["no_commits", "squash_conflict", "squash_failed"]
    message: str


# =============================================================================
# Update PR Operation Types
# =============================================================================

# Update PR uses dict[str, Any] for flexibility, no specific types needed


# =============================================================================
# Land PR Operation Types
# =============================================================================

LandPrErrorType = Literal[
    "parent_not_trunk",
    "no_pr_found",
    "pr_not_open",
    "merge_failed",
]


class LandPrSuccess(TypedDict):
    """Success result from landing a PR."""

    success: Literal[True]
    pr_number: int
    branch_name: str
    message: str


class LandPrError(TypedDict):
    """Error result from landing a PR."""

    success: Literal[False]
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


class PrepResult(TypedDict):
    """Success result from prep phase."""

    success: Literal[True]
    diff_file: str
    repo_root: str
    current_branch: str
    parent_branch: str
    commit_count: int
    squashed: bool
    message: str


class PrepError(TypedDict):
    """Error result from prep phase."""

    success: Literal[False]
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


class PreAnalysisResult(TypedDict):
    """Success result from pre-analysis phase."""

    success: Literal[True]
    branch_name: str
    parent_branch: str
    commit_count: int
    squashed: bool
    uncommitted_changes_committed: bool
    message: str
    has_conflicts: NotRequired[bool]
    conflict_details: NotRequired[dict[str, str] | None]


class PreAnalysisError(TypedDict):
    """Error result from pre-analysis phase."""

    success: Literal[False]
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, str | bool]


class PostAnalysisResult(TypedDict):
    """Success result from post-analysis phase."""

    success: Literal[True]
    pr_number: int | None
    pr_url: str
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str


class PostAnalysisError(TypedDict):
    """Error result from post-analysis phase."""

    success: Literal[False]
    error_type: PostAnalysisErrorType
    message: str
    details: dict[str, str]


class PreflightResult(TypedDict):
    """Result from preflight phase (pre-analysis + submit + diff extraction)."""

    success: Literal[True]
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


class FinalizeResult(TypedDict):
    """Result from finalize phase (update PR metadata)."""

    success: Literal[True]
    pr_number: int
    pr_url: str
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str
