"""CLI error handling for non-ideal-state type narrowing.

This module provides the EnsureIdeal class for narrowing types from operations
that can return non-ideal states (like PR lookups, branch detection, API calls).

Unlike ensure.py which contains invariant/precondition checks, this module
contains methods that narrow discriminated union types by handling non-ideal
cases and exiting with user-friendly errors.
"""

from __future__ import annotations

from typing import TypeVar

import click

from erk_shared.gateway.github.types import PRDetails, PRNotFound
from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    NonIdealState,
    NoPRForBranch,
    PRNotFoundError,
    SessionNotFound,
)
from erk_shared.output.output import user_output

T = TypeVar("T")


class EnsureIdeal:
    """Helper class for narrowing non-ideal-state discriminated unions."""

    @staticmethod
    def ideal_state(result: T | NonIdealState) -> T:
        """Ensure result is not a NonIdealState, otherwise exit with error.

        This method provides type narrowing: it takes `T | NonIdealState` and
        returns `T`, allowing the type checker to understand the value cannot
        be a NonIdealState after this call.

        Args:
            result: Value that may be a NonIdealState

        Returns:
            The value unchanged if not NonIdealState (with narrowed type T)

        Raises:
            SystemExit: If result is NonIdealState (with exit code 1)

        Example:
            >>> from erk_shared.non_ideal_state import GitHubChecks
            >>> branch = EnsureIdeal.ideal_state(GitHubChecks.branch(raw_branch))
            >>> # branch is now guaranteed to be str, not str | BranchDetectionFailed
        """
        if isinstance(result, NonIdealState):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def branch(result: str | BranchDetectionFailed) -> str:
        """Ensure branch detection succeeded.

        Args:
            result: Branch name or BranchDetectionFailed

        Returns:
            The branch name

        Raises:
            SystemExit: If detection failed (with exit code 1)
        """
        if isinstance(result, BranchDetectionFailed):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def pr(result: PRDetails | NoPRForBranch | PRNotFoundError) -> PRDetails:
        """Ensure PR lookup succeeded.

        Args:
            result: PRDetails or a not-found error

        Returns:
            The PRDetails

        Raises:
            SystemExit: If PR not found (with exit code 1)
        """
        if isinstance(result, (NoPRForBranch, PRNotFoundError)):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def unwrap_pr(result: PRDetails | PRNotFound, message: str) -> PRDetails:
        """Ensure PR lookup returned a valid PR.

        Unlike EnsureIdeal.pr() which works with NonIdealState types that have
        built-in messages, this method works with PRNotFound sentinel from
        github.types and requires the caller to provide the error message.

        Args:
            result: PRDetails or PRNotFound sentinel
            message: Error message if not found

        Returns:
            The PRDetails

        Raises:
            SystemExit: If PR not found (with exit code 1)
        """
        if isinstance(result, PRNotFound):
            user_output(click.style("Error: ", fg="red") + message)
            raise SystemExit(1)
        return result

    @staticmethod
    def comments(result: list | GitHubAPIFailed) -> list:
        """Ensure comments fetch succeeded.

        Args:
            result: List of comments or GitHubAPIFailed

        Returns:
            The list of comments

        Raises:
            SystemExit: If API call failed (with exit code 1)
        """
        if isinstance(result, GitHubAPIFailed):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def void_op(result: None | GitHubAPIFailed) -> None:
        """Ensure void operation succeeded.

        Args:
            result: None (success) or GitHubAPIFailed

        Returns:
            None

        Raises:
            SystemExit: If API call failed (with exit code 1)
        """
        if isinstance(result, GitHubAPIFailed):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def session(result: T | SessionNotFound) -> T:
        """Ensure session lookup succeeded.

        Args:
            result: Session or SessionNotFound sentinel

        Returns:
            The Session

        Raises:
            SystemExit: If session not found (with exit code 1)
        """
        if isinstance(result, SessionNotFound):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result
