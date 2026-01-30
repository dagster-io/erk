"""Discriminated union types for Git remote operations.

PushResult | PushError and PullRebaseResult | PullRebaseError follow
the NonIdealState pattern established by MergeResult | MergeError.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PushResult:
    """Success result from pushing to remote."""


@dataclass(frozen=True)
class PushError:
    """Error result from pushing to remote. Implements NonIdealState."""

    message: str

    @property
    def error_type(self) -> str:
        return "push-failed"


@dataclass(frozen=True)
class PullRebaseResult:
    """Success result from pull --rebase."""


@dataclass(frozen=True)
class PullRebaseError:
    """Error result from pull --rebase. Implements NonIdealState."""

    message: str

    @property
    def error_type(self) -> str:
        return "pull-rebase-failed"
