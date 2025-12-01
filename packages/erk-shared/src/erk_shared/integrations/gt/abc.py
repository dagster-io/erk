"""Abstract operations interfaces for GT kit subprocess commands.

This module defines ABC interfaces for Graphite (gt) and GitHub (gh) operations
used by GT kit CLI commands. These interfaces enable dependency injection with
in-memory fakes for testing while maintaining type safety.

Design:
- Composite GtKit interface that combines Git, GitHub, and main_graphite()
- Return values match existing subprocess patterns (str | None, bool, etc.)
- LBYL pattern: operations check state, return None/False on failure

Note: Git operations are provided by the core Git interface from erk_shared.git.abc.
GitHub operations use the main GitHub ABC from erk_shared.github.
"""

from abc import ABC, abstractmethod

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.integrations.graphite.abc import Graphite


class GtKit(ABC):
    """Composite interface combining all GT kit operations.

    This interface provides a single injection point for all git, Graphite,
    and GitHub operations used by GT kit CLI commands.

    GitHub operations use the main GitHub ABC from erk_shared.github which
    provides methods that take repo_root as a parameter rather than operating
    on the "current" branch.
    """

    @abstractmethod
    def git(self) -> Git:
        """Get the git operations interface.

        Returns:
            Git implementation
        """

    @abstractmethod
    def github(self) -> GitHub:
        """Get the GitHub operations interface.

        Returns:
            GitHub implementation from erk_shared.github
        """

    @abstractmethod
    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface.

        Returns:
            Graphite implementation for full graphite operations
        """
