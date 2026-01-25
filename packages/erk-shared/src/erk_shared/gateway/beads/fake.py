"""In-memory fake implementation of Beads gateway for testing."""

from erk_shared.gateway.beads.abc import BeadsGateway
from erk_shared.gateway.beads.types import BeadsIssue


class FakeBeadsGateway(BeadsGateway):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    """

    def __init__(
        self,
        *,
        issues: list[BeadsIssue] | None,
    ) -> None:
        """Create FakeBeadsGateway with pre-configured state.

        Args:
            issues: List of BeadsIssue to return from queries.
        """
        self._issues = issues if issues is not None else []

    def list_issues(
        self,
        *,
        labels: list[str] | None,
        status: str | None,
        limit: int | None,
    ) -> list[BeadsIssue]:
        """Query issues from in-memory storage.

        Filters issues by labels (AND logic) and status.
        """
        issues = list(self._issues)

        # Filter by labels (AND logic - issue must have ALL specified labels)
        if labels:
            label_set = set(labels)
            issues = [issue for issue in issues if label_set.issubset(set(issue.labels))]

        # Filter by status
        if status is not None:
            issues = [issue for issue in issues if issue.status == status]

        # Apply limit
        if limit is not None:
            issues = issues[:limit]

        return issues
