"""Non-ideal state types for operations that can fail gracefully.

This module provides:
- NonIdealState: Marker interface for error states (Protocol)
- NonIdealStateError: Exception raised by NonIdealState.ensure()
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

    # Or raise immediately
    result = some_operation()
    if isinstance(result, NonIdealState):
        result.ensure()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn, Protocol, runtime_checkable


class NonIdealStateError(Exception):
    """Raised by NonIdealState.ensure() when a non-ideal state is encountered."""

    def __init__(self, state: NonIdealState) -> None:
        self.error_type = state.error_type
        super().__init__(state.message)


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

    def ensure(self) -> NoReturn:
        """Raise NonIdealStateError with this state's details."""
        raise NonIdealStateError(self)


@dataclass(frozen=True)
class BranchDetectionFailed:
    """Branch could not be detected from current directory."""

    @property
    def error_type(self) -> str:
        return "branch-detection-failed"

    @property
    def message(self) -> str:
        return "Could not determine current branch"

    def ensure(self) -> NoReturn:
        raise NonIdealStateError(self)


@dataclass(frozen=True)
class NoPRForBranch:
    """No PR exists for the specified branch."""

    branch: str

    @property
    def error_type(self) -> str:
        return "no-pr-for-branch"

    @property
    def message(self) -> str:
        return f"No PR found for branch '{self.branch}'"

    def ensure(self) -> NoReturn:
        raise NonIdealStateError(self)


@dataclass(frozen=True)
class PRNotFoundError:
    """PR with specified number does not exist."""

    pr_number: int

    @property
    def error_type(self) -> str:
        return "pr-not-found"

    @property
    def message(self) -> str:
        return f"PR #{self.pr_number} not found"

    def ensure(self) -> NoReturn:
        raise NonIdealStateError(self)


@dataclass(frozen=True)
class GitHubAPIFailed:
    """GitHub API call failed with an error."""

    message: str

    @property
    def error_type(self) -> str:
        return "github-api-failed"

    def ensure(self) -> NoReturn:
        raise NonIdealStateError(self)


@dataclass(frozen=True)
class SessionNotFound:
    """Session with specified ID does not exist."""

    session_id: str

    @property
    def error_type(self) -> str:
        return "session-not-found"

    @property
    def message(self) -> str:
        return f"Session not found: {self.session_id}"

    def ensure(self) -> NoReturn:
        raise NonIdealStateError(self)
