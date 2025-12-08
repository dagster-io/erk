"""Non-ideal state types for operations that can fail gracefully.

This module provides:
- NonIdealState: Marker interface for error states (Protocol)
- Specific error classes: BranchDetectionFailed, NoPRForBranch, etc.

The NonIdealState pattern allows functions to return T | NonIdealState,
letting callers decide how to handle errors (exit, log, retry, etc.)
rather than forcing early exit.

Usage:
    from erk_shared.non_ideal_state import NonIdealState, BranchDetectionFailed

    # Check if result is a non-ideal state
    result = some_operation()
    if isinstance(result, NonIdealState):
        print(f"Error: {result.message}")
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class NonIdealState(Protocol):
    """Marker interface for non-ideal states.

    All NonIdealState implementations must provide error_type and message
    properties for consistent error handling.
    """

    @property
    def error_type(self) -> str: ...

    @property
    def message(self) -> str: ...


@dataclass(frozen=True)
class BranchDetectionFailed:
    """Branch could not be detected from current directory."""

    @property
    def error_type(self) -> str:
        return "branch_detection_failed"

    @property
    def message(self) -> str:
        return "Could not determine current branch"


@dataclass(frozen=True)
class NoPRForBranch:
    """No PR exists for the specified branch."""

    branch: str

    @property
    def error_type(self) -> str:
        return "no_pr_for_branch"

    @property
    def message(self) -> str:
        return f"No PR found for branch '{self.branch}'"


@dataclass(frozen=True)
class PRNotFoundError:
    """PR with specified number does not exist."""

    pr_number: int

    @property
    def error_type(self) -> str:
        return "pr_not_found"

    @property
    def message(self) -> str:
        return f"PR #{self.pr_number} not found"


@dataclass(frozen=True)
class GitHubAPIFailed:
    """GitHub API call failed with an error."""

    _message: str

    @property
    def error_type(self) -> str:
        return "github_api_failed"

    @property
    def message(self) -> str:
        return self._message
