"""In-memory fake implementation of Beads gateway for testing."""

import uuid

from erk_shared.gateway.beads.abc import BeadsGateway
from erk_shared.gateway.beads.types import BeadsIssue
from erk_shared.gateway.time.abc import Time


class FakeBeadsGateway(BeadsGateway):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    """

    def __init__(
        self,
        *,
        time: Time,
        issues: list[BeadsIssue] | None,
    ) -> None:
        """Create FakeBeadsGateway with pre-configured state.

        Args:
            time: Time abstraction for deterministic timestamps.
            issues: List of BeadsIssue to return from queries.
        """
        self._time = time
        self._issues: list[BeadsIssue] = list(issues) if issues is not None else []

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

    def create_issue(
        self,
        *,
        title: str,
        labels: list[str] | None,
        description: str | None,
    ) -> BeadsIssue:
        """Create a new issue in in-memory storage.

        Generates a fake ID, uses injected Time for timestamps,
        and appends to internal issues list.
        """
        issue_id = f"bd-{uuid.uuid4().hex[:8]}"
        timestamp = self._time.now().isoformat()

        issue = BeadsIssue(
            id=issue_id,
            title=title,
            description=description if description is not None else "",
            status="open",
            labels=tuple(labels) if labels else (),
            assignee=None,
            notes="",
            created_at=timestamp,
            updated_at=timestamp,
        )

        self._issues.append(issue)
        return issue
