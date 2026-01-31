"""Type definitions for BranchManager operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrInfo:
    """PR information returned by BranchManager.

    This is a simplified PR info type for statusline use cases,
    containing only the fields needed for display.
    """

    number: int
    state: str  # "OPEN", "MERGED", "CLOSED"
    is_draft: bool
    from_fallback: bool  # True if fetched via GitHub API fallback (not from cache)


@dataclass(frozen=True)
class SubmitBranchResult:
    """Success result from submitting a branch."""


@dataclass(frozen=True)
class SubmitBranchError:
    """Error result from submitting a branch. Implements NonIdealState."""

    message: str

    @property
    def error_type(self) -> str:
        return "submit-branch-failed"
