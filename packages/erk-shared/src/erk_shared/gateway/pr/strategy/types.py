"""Type definitions for PR submit strategy operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitStrategyResult:
    """Result from any submit strategy.

    Represents a successful PR submission regardless of which strategy
    was used (Graphite-first or core flow).

    Attributes:
        pr_number: The GitHub PR number
        base_branch: The base/parent branch for the PR
        graphite_url: Graphite PR URL (None for core flow)
        pr_url: GitHub PR URL
        branch_name: The branch that was submitted
        was_created: True if PR was created, False if updated existing PR
    """

    pr_number: int
    base_branch: str
    graphite_url: str | None
    pr_url: str
    branch_name: str
    was_created: bool


@dataclass(frozen=True)
class SubmitStrategyError:
    """Error from submit strategy.

    Represents a failure in the submit strategy. The error_type provides
    a machine-readable category while message provides human-readable details.

    Attributes:
        error_type: Category of error (e.g., "detached_head", "gt_submit_failed")
        message: Human-readable error message
        details: Additional context as key-value pairs
    """

    error_type: str
    message: str
    details: dict[str, str]
