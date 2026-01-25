"""Result types for PR submission strategies.

These types represent the unified outcome of any PR submission strategy,
whether Graphite-first or core git+gh. The strategy pattern requires a
common result type so callers can handle results uniformly.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SubmitStrategyResult:
    """Successful result from any PR submission strategy.

    This is the unified success type for all strategies. Each field has a
    consistent meaning regardless of which strategy produced it.

    Attributes:
        status: Always "success" for type narrowing
        pr_number: The GitHub PR number
        base_branch: The branch the PR targets (parent branch or trunk)
        graphite_url: Graphite visualization URL (None for core strategy)
        pr_url: GitHub PR URL
        branch_name: The source branch name
        was_created: True if PR was created, False if updated existing PR
    """

    status: Literal["success"]
    pr_number: int
    base_branch: str
    graphite_url: str | None
    pr_url: str
    branch_name: str
    was_created: bool


@dataclass(frozen=True)
class SubmitStrategyError:
    """Error result from any PR submission strategy.

    This is the unified error type for all strategies. The error_type field
    uses consistent codes across strategies for programmatic handling.

    Attributes:
        status: Always "error" for type narrowing
        error_type: Categorizes the error (e.g., "no_branch", "push_failed")
        message: Human-readable error description
        details: Additional context (strategy-specific, for debugging)
    """

    status: Literal["error"]
    error_type: str
    message: str
    details: dict[str, str]
