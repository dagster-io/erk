"""Data types for GitHub issues integration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IssueInfo:
    """Information about a GitHub issue."""

    number: int
    title: str
    body: str
    state: str  # "OPEN" or "CLOSED"
    url: str
    labels: list[str]
    assignees: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CreateIssueResult:
    """Result from creating a GitHub issue.

    Attributes:
        number: Issue number (e.g., 123)
        url: Full GitHub URL (e.g., https://github.com/owner/repo/issues/123)
    """

    number: int
    url: str


@dataclass(frozen=True)
class IssueComment:
    """A comment on a GitHub issue.

    Attributes:
        body: Markdown body of the comment
        url: Full GitHub URL to the comment (html_url)
    """

    body: str
    url: str
