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
