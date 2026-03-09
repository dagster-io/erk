"""Tests for PlannedPRPlanListService HTTP path (_get_plan_list_data_http)."""

from pathlib import Path

from erk.core.services.plan_list_service import PlannedPRPlanListService
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.http import FakeHttpClient
from tests.fakes.gateway.time import FakeTime

TEST_LOCATION = GitHubRepoLocation(root=Path("/test/repo"), repo_id=GitHubRepoId("owner", "repo"))


def _make_rest_issue_pr(
    *,
    number: int,
    title: str = "Plan PR",
    body: str = "metadata\n\n---\n\n# Plan\n\nContent",
    labels: list[str] | None = None,
) -> dict:
    """Build a REST API issue item that looks like a PR."""
    return {
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "state": "open",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T14:00:00Z",
        "labels": [{"name": label} for label in (labels or ["erk-plan"])],
        "user": {"login": "test-user"},
        "pull_request": {"head": {"ref": f"plan-branch-{number}"}},
    }


def _make_graphql_enrichment(pr_numbers: list[int]) -> dict:
    """Build a fake GraphQL enrichment response."""
    repo_data = {}
    for num in pr_numbers:
        repo_data[f"pr_{num}"] = {
            "isDraft": True,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "isCrossRepository": False,
            "baseRefName": "main",
            "headRefName": f"plan-branch-{num}",
            "statusCheckRollup": {"state": "SUCCESS"},
            "reviewThreads": {"totalCount": 0, "nodes": []},
            "reviewDecision": "APPROVED",
        }
    return {"data": {"repository": repo_data}}


def _setup_http_client_for_plan(
    *,
    rest_items: list[dict],
    pr_numbers: list[int],
) -> FakeHttpClient:
    """Configure FakeHttpClient with REST + GraphQL responses."""
    client = FakeHttpClient()
    client.set_list_response(
        "repos/owner/repo/issues?labels=erk-plan&state=open&per_page=100&sort=updated&direction=desc",
        response=rest_items,
    )
    client.set_response("graphql", response=_make_graphql_enrichment(pr_numbers))
    return client


def test_http_path_returns_plan_for_pr() -> None:
    """HTTP path fetches REST issues and enriches via GraphQL."""
    rest_items = [_make_rest_issue_pr(number=42, title="My Plan")]
    http_client = _setup_http_client_for_plan(rest_items=rest_items, pr_numbers=[42])

    service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=http_client,
    )

    assert len(result.plans) == 1
    assert result.plans[0].pr_identifier == "42"


def test_http_path_empty_response() -> None:
    """HTTP path with no issues returns empty data."""
    http_client = FakeHttpClient()
    http_client.set_list_response(
        "repos/owner/repo/issues?labels=erk-plan&state=open&per_page=100&sort=updated&direction=desc",
        response=[],
    )

    service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=http_client,
    )

    assert result.plans == []
    assert result.pr_linkages == {}


def test_http_path_filters_non_pr_items() -> None:
    """HTTP path filters out issues without pull_request key."""
    issue_without_pr = {
        "number": 99,
        "title": "Not a PR",
        "body": "body",
        "html_url": "https://github.com/owner/repo/issues/99",
        "state": "open",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T14:00:00Z",
        "labels": [{"name": "erk-plan"}],
        "user": {"login": "test-user"},
    }
    pr_item = _make_rest_issue_pr(number=42)

    http_client = FakeHttpClient()
    http_client.set_list_response(
        "repos/owner/repo/issues?labels=erk-plan&state=open&per_page=100&sort=updated&direction=desc",
        response=[issue_without_pr, pr_item],
    )
    http_client.set_response("graphql", response=_make_graphql_enrichment([42]))

    service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=http_client,
    )

    assert len(result.plans) == 1
    assert result.plans[0].pr_identifier == "42"


def test_http_path_excludes_labels() -> None:
    """HTTP path applies client-side exclude_labels filtering."""
    items = [
        _make_rest_issue_pr(number=1, labels=["erk-plan"]),
        _make_rest_issue_pr(number=2, labels=["erk-plan", "erk-learn"]),
    ]

    http_client = FakeHttpClient()
    http_client.set_list_response(
        "repos/owner/repo/issues?labels=erk-plan&state=open&per_page=100&sort=updated&direction=desc",
        response=items,
    )
    http_client.set_response("graphql", response=_make_graphql_enrichment([1]))

    service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        exclude_labels=["erk-learn"],
        http_client=http_client,
    )

    assert len(result.plans) == 1
    assert result.plans[0].pr_identifier == "1"


def test_http_path_populates_timing_data() -> None:
    """HTTP path populates api_ms timing in result."""
    rest_items = [_make_rest_issue_pr(number=42)]
    http_client = _setup_http_client_for_plan(rest_items=rest_items, pr_numbers=[42])

    service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=http_client,
    )

    assert result.api_ms is not None
    assert result.api_ms >= 0


def test_http_path_skip_workflow_runs() -> None:
    """HTTP path skips workflow runs when requested."""
    rest_items = [_make_rest_issue_pr(number=42)]
    http_client = _setup_http_client_for_plan(rest_items=rest_items, pr_numbers=[42])

    service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        skip_workflow_runs=True,
        http_client=http_client,
    )

    assert result.workflow_runs == {}
