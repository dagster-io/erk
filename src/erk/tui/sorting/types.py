"""Sort state types for TUI dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class SortKey(Enum):
    """Available sort keys for plan list."""

    ISSUE_NUMBER = auto()  # Default: sort by issue number (descending)
    BRANCH_ACTIVITY = auto()  # Sort by most recent commit on branch


@dataclass(frozen=True)
class BranchActivity:
    """Branch activity data for a plan.

    Represents the most recent commit on the branch (not in trunk),
    indicating how recently the branch was worked on.

    Attributes:
        last_commit_at: Timestamp of most recent commit on branch, None if no commits
        last_commit_author: Author of most recent commit, None if no commits
    """

    last_commit_at: datetime | None
    last_commit_author: str | None

    @staticmethod
    def empty() -> BranchActivity:
        """Create empty activity (no commits on branch)."""
        return BranchActivity(last_commit_at=None, last_commit_author=None)


@dataclass(frozen=True)
class SortState:
    """State for sort mode.

    Attributes:
        key: Current sort key
    """

    key: SortKey

    @staticmethod
    def initial() -> SortState:
        """Create initial state with default sort (by issue number)."""
        return SortState(key=SortKey.ISSUE_NUMBER)

    def toggle(self) -> SortState:
        """Toggle between sort keys.

        Returns:
            New state with next sort key
        """
        if self.key == SortKey.ISSUE_NUMBER:
            return SortState(key=SortKey.BRANCH_ACTIVITY)
        return SortState(key=SortKey.ISSUE_NUMBER)

    @property
    def display_label(self) -> str:
        """Get display label for current sort mode."""
        if self.key == SortKey.ISSUE_NUMBER:
            return "by issue#"
        return "by recent activity"
