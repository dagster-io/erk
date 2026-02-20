"""Unit tests for RealGitHub parsing methods."""

from datetime import UTC, datetime

from erk_shared.gateway.github.real import RealGitHub
from erk_shared.gateway.github.types import GitHubRepoId, RepoInfo


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


# --- Tests for _parse_plan_prs_with_details (GraphQL response parsing) ---


def _make_graphql_pr_node(
    *,
    number: int = 100,
    title: str = "Test PR",
    body: str = "",
    state: str = "OPEN",
    is_draft: bool = False,
    author_login: str = "test-user",
    head_ref: str = "feature-branch",
    base_ref: str = "master",
    created_at: str = "2024-03-15T10:00:00Z",
    updated_at: str = "2024-03-16T12:00:00Z",
) -> dict:
    """Create a PR node matching GitHub GraphQL pullRequests response shape."""
    return {
        "number": number,
        "url": f"https://github.com/owner/repo/pull/{number}",
        "title": title,
        "body": body,
        "state": state,
        "isDraft": is_draft,
        "baseRefName": base_ref,
        "headRefName": head_ref,
        "isCrossRepository": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "createdAt": created_at,
        "updatedAt": updated_at,
        "author": {"login": author_login},
        "labels": {"nodes": []},
        "statusCheckRollup": None,
        "reviewThreads": {"nodes": []},
    }


def _wrap_graphql_response(nodes: list[dict]) -> dict:
    """Wrap PR nodes in the expected GraphQL response structure."""
    return {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": nodes,
                }
            }
        }
    }


def test_parse_plan_prs_returns_both_draft_and_non_draft() -> None:
    """Both draft and non-draft PRs are returned (no draft filtering)."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="owner", repo="repo")

    response = _wrap_graphql_response(
        [
            _make_graphql_pr_node(number=1, is_draft=True, title="Draft PR"),
            _make_graphql_pr_node(number=2, is_draft=False, title="Ready PR"),
        ]
    )

    pr_details, pr_linkages = github._parse_plan_prs_with_details(response, repo_id, author=None)

    assert len(pr_details) == 2
    numbers = {pr.number for pr in pr_details}
    assert numbers == {1, 2}


def test_parse_plan_prs_preserves_is_draft_state() -> None:
    """is_draft field is correctly set on both PRDetails and PullRequestInfo."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="owner", repo="repo")

    response = _wrap_graphql_response(
        [
            _make_graphql_pr_node(number=1, is_draft=True),
            _make_graphql_pr_node(number=2, is_draft=False),
        ]
    )

    pr_details, pr_linkages = github._parse_plan_prs_with_details(response, repo_id, author=None)

    draft_pr = next(pr for pr in pr_details if pr.number == 1)
    ready_pr = next(pr for pr in pr_details if pr.number == 2)
    assert draft_pr.is_draft is True
    assert ready_pr.is_draft is False

    # PullRequestInfo also carries is_draft
    assert pr_linkages[1][0].is_draft is True
    assert pr_linkages[2][0].is_draft is False


def test_parse_plan_prs_filters_by_author() -> None:
    """Author filter excludes PRs from other authors."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="owner", repo="repo")

    response = _wrap_graphql_response(
        [
            _make_graphql_pr_node(number=1, author_login="alice"),
            _make_graphql_pr_node(number=2, author_login="bob"),
        ]
    )

    pr_details, _ = github._parse_plan_prs_with_details(response, repo_id, author="alice")

    assert len(pr_details) == 1
    assert pr_details[0].number == 1


def test_parse_plan_prs_empty_response() -> None:
    """Empty repository data returns empty results."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="owner", repo="repo")

    response = {"data": {"repository": None}}

    pr_details, pr_linkages = github._parse_plan_prs_with_details(response, repo_id, author=None)

    assert pr_details == []
    assert pr_linkages == {}
