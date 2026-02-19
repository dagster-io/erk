"""Unit tests for RealGitHub parsing methods."""

from datetime import UTC, datetime

from erk_shared.gateway.github.real import RealGitHub
from erk_shared.gateway.github.types import RepoInfo


def _make_pr_data(
    *,
    number: int = 42,
    title: str = "Test PR",
    body: str = "PR body",
    state: str = "open",
    merged: bool = False,
    created_at: str = "2024-03-15T10:00:00Z",
    updated_at: str = "2024-03-16T12:00:00Z",
    user_login: str | None = "octocat",
    draft: bool = False,
) -> dict:
    """Create minimal PR data dict matching GitHub REST API response shape."""
    user: dict | None = {"login": user_login} if user_login is not None else None
    return {
        "number": number,
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "title": title,
        "body": body,
        "state": state,
        "merged": merged,
        "draft": draft,
        "mergeable": True,
        "mergeable_state": "clean",
        "labels": [],
        "created_at": created_at,
        "updated_at": updated_at,
        "user": user,
        "base": {"ref": "master"},
        "head": {"ref": "feature-branch", "repo": {"fork": False}},
    }


def test_parses_timestamps_from_iso_string() -> None:
    """Valid ISO timestamp strings are parsed into timezone-aware datetimes."""
    github = RealGitHub.for_test()
    repo_info = RepoInfo(owner="owner", name="repo")

    data = _make_pr_data(
        created_at="2024-03-15T10:00:00Z",
        updated_at="2024-03-16T12:30:00Z",
    )
    pr = github._parse_pr_details_from_rest_api(data, repo_info)

    assert pr.created_at == datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)
    assert pr.updated_at == datetime(2024, 3, 16, 12, 30, 0, tzinfo=UTC)


def test_uses_epoch_sentinel_when_timestamps_missing() -> None:
    """Missing timestamp strings fall back to the epoch sentinel datetime."""
    github = RealGitHub.for_test()
    repo_info = RepoInfo(owner="owner", name="repo")

    data = _make_pr_data(created_at="", updated_at="")
    pr = github._parse_pr_details_from_rest_api(data, repo_info)

    epoch = datetime(2000, 1, 1, tzinfo=UTC)
    assert pr.created_at == epoch
    assert pr.updated_at == epoch


def test_extracts_author_from_user_login() -> None:
    """Author is extracted from the user.login field."""
    github = RealGitHub.for_test()
    repo_info = RepoInfo(owner="owner", name="repo")

    data = _make_pr_data(user_login="octocat")
    pr = github._parse_pr_details_from_rest_api(data, repo_info)

    assert pr.author == "octocat"


def test_author_empty_when_user_is_none() -> None:
    """Author is empty string when the user object is None (e.g., deleted account)."""
    github = RealGitHub.for_test()
    repo_info = RepoInfo(owner="owner", name="repo")

    data = _make_pr_data(user_login=None)
    pr = github._parse_pr_details_from_rest_api(data, repo_info)

    assert pr.author == ""
