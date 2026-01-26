"""Shared fixtures for RealGitHubIssues tests."""

from pathlib import Path

import pytest

from erk_shared.gateway.github.issues.real import RealGitHubIssues
from erk_shared.gateway.time.real import RealTime


@pytest.fixture
def issues() -> RealGitHubIssues:
    """Create a RealGitHubIssues instance for testing."""
    return RealGitHubIssues(target_repo=None, time=RealTime())


@pytest.fixture
def repo_path() -> Path:
    """Return a standard repo path for tests."""
    return Path("/repo")


def make_rest_api_issue(
    number: int,
    title: str = "Test Issue",
    body: str = "Test body",
    state: str = "open",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    author: str = "testuser",
) -> dict:
    """Create a REST API issue response dict."""
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "labels": [{"name": label} for label in (labels or [])],
        "assignees": [{"login": user} for user in (assignees or [])],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "user": {"login": author},
    }
