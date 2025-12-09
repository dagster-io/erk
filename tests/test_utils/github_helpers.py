"""Test utilities for GitHub issue operations."""

from datetime import UTC, datetime

from erk_shared.github.issues import IssueInfo


def create_test_issue(
    number: int,
    title: str = "Test Issue",
    body: str = "",
    state: str = "OPEN",
    url: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    author: str = "test-user",
) -> IssueInfo:
    """Factory for creating IssueInfo instances in tests with sensible defaults.

    Args:
        number: Issue number
        title: Issue title (defaults to "Test Issue")
        body: Issue body (defaults to empty string)
        state: Issue state (defaults to "OPEN")
        url: Issue URL (defaults to auto-generated GitHub URL)
        labels: List of labels (defaults to empty list)
        assignees: List of assignees (defaults to empty list)
        created_at: Creation timestamp (defaults to 2024-01-01)
        updated_at: Update timestamp (defaults to 2024-01-01)
        author: Author username (defaults to "test-user")

    Returns:
        IssueInfo instance with provided or default values
    """
    if url is None:
        url = f"https://github.com/owner/repo/issues/{number}"
    if labels is None:
        labels = []
    if assignees is None:
        assignees = []
    if created_at is None:
        created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    if updated_at is None:
        updated_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=url,
        labels=labels,
        assignees=assignees,
        created_at=created_at,
        updated_at=updated_at,
        author=author,
    )
