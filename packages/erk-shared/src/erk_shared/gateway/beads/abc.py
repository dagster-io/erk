"""Abstract interface for Beads (bd) issue operations."""

from abc import ABC, abstractmethod

from erk_shared.gateway.beads.types import BeadsIssue


class BeadsGateway(ABC):
    """Abstract interface for Beads (bd) issue operations.

    All implementations (real, fake, dry_run, printing) must implement this interface.

    Note: Unlike GitHubIssues which needs repo_root for gh CLI context, Beads operates
    on the current directory's .beads/ folder. The bd command finds .beads/ similarly
    to how git finds .git/.
    """

    @abstractmethod
    def list_issues(
        self,
        *,
        labels: list[str] | None,
        status: str | None,
        limit: int | None,
    ) -> list[BeadsIssue]:
        """Query issues by criteria.

        Args:
            labels: Filter by labels (all labels must match)
            status: Filter by status (open, in_progress, blocked, deferred, closed, tombstone)
            limit: Maximum number of issues to return (None = no limit)

        Returns:
            List of BeadsIssue matching the criteria
        """
        ...
