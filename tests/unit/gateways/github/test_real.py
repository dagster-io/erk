"""Unit tests for RealGitHub parsing and caching methods."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

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


# --- Tests for _get_default_branch (caching + REST API call) ---
#
# These tests patch execute_gh_command_with_retry at the module level to avoid
# subprocess invocations. This follows the same pattern as test_subprocess_utils.py
# which patches run_subprocess_with_context for testing gh command infrastructure.


@patch("erk_shared.gateway.github.real.execute_gh_command_with_retry")
def test_get_default_branch_returns_branch(mock_execute) -> None:  # noqa: ANN001
    """First call fetches the default branch via REST API and returns it."""
    mock_execute.return_value = "main\n"
    github = RealGitHub.for_test()
    repo_root = Path("/test/repo")

    result = github._get_default_branch(repo_root)

    assert result == "main"
    mock_execute.assert_called_once()


@patch("erk_shared.gateway.github.real.execute_gh_command_with_retry")
def test_get_default_branch_caches_result(mock_execute) -> None:  # noqa: ANN001
    """Second call for the same repo_root returns cached result without API call."""
    mock_execute.return_value = "main\n"
    github = RealGitHub.for_test()
    repo_root = Path("/test/repo")

    first = github._get_default_branch(repo_root)
    second = github._get_default_branch(repo_root)

    assert first == "main"
    assert second == "main"
    # Only one API call — second was served from cache
    mock_execute.assert_called_once()


@patch("erk_shared.gateway.github.real.execute_gh_command_with_retry")
def test_get_default_branch_separate_cache_per_repo(mock_execute) -> None:  # noqa: ANN001
    """Different repo_root paths get independent cache entries."""
    mock_execute.side_effect = ["main\n", "master\n"]
    github = RealGitHub.for_test()
    repo_a = Path("/test/repo-a")
    repo_b = Path("/test/repo-b")

    result_a = github._get_default_branch(repo_a)
    result_b = github._get_default_branch(repo_b)

    assert result_a == "main"
    assert result_b == "master"
    assert mock_execute.call_count == 2

    # Subsequent calls use cache — no additional API calls
    assert github._get_default_branch(repo_a) == "main"
    assert github._get_default_branch(repo_b) == "master"
    assert mock_execute.call_count == 2


@patch("erk_shared.gateway.github.real.execute_gh_command_with_retry")
def test_get_default_branch_strips_whitespace(mock_execute) -> None:  # noqa: ANN001
    """Trailing whitespace/newlines from API stdout are stripped."""
    mock_execute.return_value = "  main  \n"
    github = RealGitHub.for_test()

    result = github._get_default_branch(Path("/test/repo"))

    assert result == "main"


@patch("erk_shared.gateway.github.real.execute_gh_command_with_retry")
def test_get_default_branch_uses_rest_api_endpoint(mock_execute) -> None:  # noqa: ANN001
    """The command uses repos/{owner}/{repo} REST endpoint with --jq filter."""
    mock_execute.return_value = "main\n"
    github = RealGitHub.for_test()
    repo_root = Path("/test/repo")

    github._get_default_branch(repo_root)

    cmd, cwd, time_impl = mock_execute.call_args.args
    assert cmd == ["gh", "api", "repos/{owner}/{repo}", "--jq", ".default_branch"]
    assert cwd == repo_root


@patch("erk_shared.gateway.github.real.execute_gh_command_with_retry")
def test_get_default_branch_propagates_runtime_error(mock_execute) -> None:  # noqa: ANN001
    """RuntimeError from the API call propagates without caching."""
    mock_execute.side_effect = RuntimeError("GitHub command failed: network error")
    github = RealGitHub.for_test()
    repo_root = Path("/test/repo")

    with pytest.raises(RuntimeError, match="network error"):
        github._get_default_branch(repo_root)

    # Error should NOT be cached — next call should retry
    assert repo_root not in github._default_branch_cache


# --- Tests for _build_issues_by_numbers_query ---


def test_build_issues_by_numbers_query_single_issue() -> None:
    """Query contains one aliased issueOrPullRequest for a single issue."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="acme", repo="widgets")

    query = github._build_issues_by_numbers_query([100], repo_id)

    assert "issue_100: issueOrPullRequest(number: 100)" in query
    assert 'repository(owner: "acme", name: "widgets")' in query


def test_build_issues_by_numbers_query_multiple_issues() -> None:
    """Query contains one alias per issue number."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="acme", repo="widgets")

    query = github._build_issues_by_numbers_query([100, 200, 300], repo_id)

    assert "issue_100: issueOrPullRequest(number: 100)" in query
    assert "issue_200: issueOrPullRequest(number: 200)" in query
    assert "issue_300: issueOrPullRequest(number: 300)" in query


# --- Tests for _parse_issues_by_numbers_response ---


def _make_issue_node(
    *,
    number: int = 100,
    title: str = "Test issue",
    state: str = "OPEN",
) -> dict:
    """Create a minimal issue node matching the GraphQL response shape."""
    return {
        "number": number,
        "title": title,
        "body": "",
        "state": state,
        "url": f"https://github.com/acme/widgets/issues/{number}",
        "author": {"login": "testuser"},
        "labels": {"nodes": [{"name": "erk-plan"}]},
        "assignees": {"nodes": []},
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-02T00:00:00Z",
        "timelineItems": {"nodes": []},
    }


def test_parse_issues_by_numbers_response_single_issue() -> None:
    """Single issue node is parsed into one IssueInfo."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="acme", repo="widgets")

    response = {
        "data": {
            "repository": {
                "issue_100": _make_issue_node(number=100, title="Plan A"),
            }
        }
    }

    issues, pr_linkages = github._parse_issues_by_numbers_response(response, repo_id)

    assert len(issues) == 1
    assert issues[0].number == 100
    assert issues[0].title == "Plan A"
    assert pr_linkages == {}


def test_parse_issues_by_numbers_response_multiple_issues() -> None:
    """Multiple issue nodes are all parsed."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="acme", repo="widgets")

    response = {
        "data": {
            "repository": {
                "issue_100": _make_issue_node(number=100),
                "issue_200": _make_issue_node(number=200),
            }
        }
    }

    issues, _ = github._parse_issues_by_numbers_response(response, repo_id)

    numbers = {i.number for i in issues}
    assert numbers == {100, 200}


def test_parse_issues_by_numbers_response_skips_null_nodes() -> None:
    """Null nodes (deleted/inaccessible issues) are skipped."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="acme", repo="widgets")

    response = {
        "data": {
            "repository": {
                "issue_100": _make_issue_node(number=100),
                "issue_999": None,
            }
        }
    }

    issues, _ = github._parse_issues_by_numbers_response(response, repo_id)

    assert len(issues) == 1
    assert issues[0].number == 100


def test_parse_issues_by_numbers_response_empty_repository() -> None:
    """Empty repository data returns empty results."""
    github = RealGitHub.for_test()
    repo_id = GitHubRepoId(owner="acme", repo="widgets")

    response = {"data": {"repository": {}}}

    issues, pr_linkages = github._parse_issues_by_numbers_response(response, repo_id)

    assert issues == []
    assert pr_linkages == {}
