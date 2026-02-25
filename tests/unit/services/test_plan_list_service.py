"""Tests for PlanListService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.core.services.plan_list_service import (
    PlanListData,
    PlannedPRPlanListService,
    RealPlanListService,
)
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.gateway.http.fake import FakeHttpClient
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.types import Plan, PlanState

TEST_LOCATION = GitHubRepoLocation(root=Path("/test/repo"), repo_id=GitHubRepoId("owner", "repo"))


class TestPlanListService:
    """Tests for PlanListService with injected fakes."""

    def test_fetches_issues_with_empty_pr_linkages(self) -> None:
        """Service uses unified query even when no PR linkages exist."""
        now = datetime.now(UTC)
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="Plan body",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "42"
        assert result.plans[0].title == "Test Plan"
        assert result.pr_linkages == {}

    def test_fetches_issues_and_pr_linkages_unified(self) -> None:
        """Service uses unified get_issues_with_pr_linkages for issues + PR linkages."""
        now = datetime.now(UTC)
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        pr = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="PR Title",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        # Configure issues and pr_issue_linkages for unified query
        fake_github = FakeGitHub(
            issues_data=[issue],
            pr_issue_linkages={42: [pr]},
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        # Unified path returns plans from get_issues_with_pr_linkages
        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "42"
        # PR linkages should be fetched together
        assert 42 in result.pr_linkages
        assert result.pr_linkages[42][0].number == 123

    def test_empty_issues_returns_empty_data(self) -> None:
        """Service returns empty data when no issues match."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_state_filter_with_unified_path(self) -> None:
        """Service passes state filter to unified get_issues_with_pr_linkages."""
        now = datetime.now(UTC)
        open_issue = IssueInfo(
            number=1,
            title="Open Plan",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/1",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        closed_issue = IssueInfo(
            number=2,
            title="Closed Plan",
            body="",
            state="CLOSED",
            url="https://github.com/owner/repo/issues/2",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        # Configure both issues for the unified query
        fake_github = FakeGitHub(issues_data=[open_issue, closed_issue])
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            state="open",
            http_client=FakeHttpClient(),
        )

        assert len(result.plans) == 1
        assert result.plans[0].title == "Open Plan"

    def test_state_filter_closed(self) -> None:
        """Service passes state filter to unified get_issues_with_pr_linkages for closed issues."""
        now = datetime.now(UTC)
        open_issue = IssueInfo(
            number=1,
            title="Open Plan",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/1",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        closed_issue = IssueInfo(
            number=2,
            title="Closed Plan",
            body="",
            state="CLOSED",
            url="https://github.com/owner/repo/issues/2",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})
        fake_github = FakeGitHub(issues_data=[open_issue, closed_issue])

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            state="closed",
            http_client=FakeHttpClient(),
        )

        assert len(result.plans) == 1
        assert result.plans[0].title == "Closed Plan"


class TestWorkflowRunFetching:
    """Tests for efficient workflow run fetching via GraphQL node_id batch API."""

    def test_fetches_workflow_runs_by_node_id(self) -> None:
        """Service uses GraphQL nodes(ids: [...]) for efficient batch fetching."""
        now = datetime.now(UTC)
        # Create issue with plan-header metadata containing node_id
        issue_body = """## Objective
Test plan

<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
created_at: '2024-01-15T10:30:00Z'
created_by: user123
worktree_name: feature-branch
last_dispatched_run_id: '12345'
last_dispatched_node_id: 'WFR_abc123'
last_dispatched_at: '2024-01-15T11:00:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body=issue_body,
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        # Pre-configure workflow run that matches the node_id
        run = WorkflowRun(
            run_id="12345",
            status="completed",
            conclusion="success",
            branch="feature-branch",
            head_sha="abc123",
            display_title="42:abc123",
            created_at=now,
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        # Configure both issues (for unified query) and workflow_runs_by_node_id
        fake_github = FakeGitHub(
            issues_data=[issue],
            workflow_runs_by_node_id={"WFR_abc123": run},
        )

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        # Verify workflow run was fetched and mapped to issue
        assert 42 in result.workflow_runs
        assert result.workflow_runs[42] is not None
        assert result.workflow_runs[42].run_id == "12345"

    def test_skips_workflow_fetch_when_skip_flag_set(self) -> None:
        """Service skips workflow fetching when skip_workflow_runs=True."""
        now = datetime.now(UTC)
        issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_abc123'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body=issue_body,
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        run = WorkflowRun(
            run_id="12345",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(
            issues_data=[issue],
            workflow_runs_by_node_id={"WFR_abc123": run},
        )

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            skip_workflow_runs=True,
            http_client=FakeHttpClient(),
        )

        # Workflow runs dict should be empty when skipped
        assert result.workflow_runs == {}

    def test_handles_missing_node_id_gracefully(self) -> None:
        """Service handles issues without node_id in body."""
        now = datetime.now(UTC)
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body="Plain body without metadata",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        # No workflow runs should be fetched (no node_ids to fetch)
        assert result.workflow_runs == {}

    def test_handles_node_id_not_found(self) -> None:
        """Service handles case where node_id not found in GraphQL results."""
        now = datetime.now(UTC)
        issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_nonexistent'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body=issue_body,
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        # No workflow runs configured - node_id won't be found
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        # Issue should have None for workflow run (not found)
        assert 42 in result.workflow_runs
        assert result.workflow_runs[42] is None

    def test_workflow_run_api_failure_returns_empty_runs(self) -> None:
        """Service continues with empty workflow runs when API fails."""
        now = datetime.now(UTC)
        issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_abc123'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        issue = IssueInfo(
            number=42,
            title="Test Plan",
            body=issue_body,
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-planned-pr", "erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        # Configure GitHub to raise an error when fetching workflow runs
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(
            issues_data=[issue],
            workflow_runs_error="Network unreachable",
        )

        service = RealPlanListService(fake_github, fake_issues, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=FakeHttpClient(),
        )

        # Plans should still be returned
        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "42"
        # Workflow runs should be empty due to API failure
        assert result.workflow_runs == {}


class TestPlanListData:
    """Tests for PlanListData dataclass."""

    def test_dataclass_is_frozen(self) -> None:
        """PlanListData instances are immutable."""
        data = PlanListData(
            plans=[],
            pr_linkages={},
            workflow_runs={},
        )

        with pytest.raises(AttributeError):
            data.plans = []  # type: ignore[misc] -- intentionally mutating frozen dataclass to test immutability

    def test_dataclass_contains_all_fields(self) -> None:
        """PlanListData has all expected fields."""
        now = datetime.now(UTC)
        plans = [
            Plan(
                plan_identifier="1",
                title="Plan",
                body="",
                state=PlanState.OPEN,
                url="",
                labels=["erk-planned-pr", "erk-plan"],
                assignees=[],
                created_at=now,
                updated_at=now,
                metadata={"number": 1},
                objective_id=None,
            )
        ]
        pr = PullRequestInfo(
            number=10,
            state="OPEN",
            url="",
            is_draft=False,
            title="PR",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        linkages = {1: [pr]}
        run = WorkflowRun(
            run_id="100",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        )
        runs: dict[int, WorkflowRun | None] = {1: run}

        data = PlanListData(
            plans=plans,
            pr_linkages=linkages,
            workflow_runs=runs,
            api_ms=150.5,
            plan_parsing_ms=42.3,
            workflow_runs_ms=88.1,
        )

        assert data.plans == plans
        assert data.pr_linkages == linkages
        assert data.workflow_runs == runs
        assert data.api_ms == 150.5
        assert data.plan_parsing_ms == 42.3
        assert data.workflow_runs_ms == 88.1

    def test_timing_fields_default_to_zero(self) -> None:
        """Timing fields default to 0.0 when not provided."""
        data = PlanListData(
            plans=[],
            pr_linkages={},
            workflow_runs={},
        )
        assert data.api_ms == 0.0
        assert data.plan_parsing_ms == 0.0
        assert data.workflow_runs_ms == 0.0


def _make_rest_item(
    *,
    number: int,
    title: str,
    body: str,
    labels: tuple[str, ...] = ("erk-plan",),
    branch: str = "plan-branch",
    author: str = "test-user",
    created_at: str = "2024-01-15T10:00:00Z",
    updated_at: str = "2024-01-15T14:00:00Z",
) -> dict:
    """Build a REST API issue item that looks like a PR for HTTP path tests."""
    return {
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "state": "open",
        "created_at": created_at,
        "updated_at": updated_at,
        "labels": [{"name": label} for label in labels],
        "user": {"login": author},
        "pull_request": {"head": {"ref": branch}},
    }


def _make_graphql_enrichment_response(
    pr_numbers: list[int],
    *,
    is_draft: bool = True,
    checks_state: str = "SUCCESS",
    review_thread_counts: tuple[int, int] | None = None,
) -> dict:
    """Build a fake GraphQL enrichment response for HTTP path tests."""
    repo_data = {}
    resolved = review_thread_counts[0] if review_thread_counts else 0
    total = review_thread_counts[1] if review_thread_counts else 0
    for num in pr_numbers:
        repo_data[f"pr_{num}"] = {
            "isDraft": is_draft,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "isCrossRepository": False,
            "baseRefName": "main",
            "headRefName": f"plan-branch-{num}",
            "statusCheckRollup": {"state": checks_state},
            "reviewThreads": {
                "totalCount": total,
                "nodes": [{"isResolved": True}] * resolved
                + [{"isResolved": False}] * (total - resolved),
            },
            "reviewDecision": "APPROVED",
        }
    return {"data": {"repository": repo_data}}


def _make_workflow_runs_graphql_response(
    node_id_to_run: dict[str, WorkflowRun],
) -> dict:
    """Build a fake GraphQL workflow runs response for HTTP path tests."""
    nodes = []
    for node_id, run in node_id_to_run.items():
        nodes.append(
            {
                "id": node_id,
                "__typename": "WorkflowRun",
                "databaseId": int(run.run_id),
                "status": run.status.upper(),
                "conclusion": run.conclusion.upper() if run.conclusion else None,
                "headBranch": run.branch,
                "headSha": run.head_sha,
                "displayTitle": run.display_title or f"Run {run.run_id}",
                "createdAt": "2024-01-15T11:00:00Z",
            }
        )
    return {"data": {"nodes": nodes}}


def _setup_planned_pr_http_client(
    *,
    rest_items: list[dict],
    pr_numbers: list[int],
    labels: str = "erk-planned-pr,erk-plan",
    is_draft: bool = True,
    checks_state: str = "SUCCESS",
    review_thread_counts: tuple[int, int] | None = None,
    workflow_runs: dict[str, WorkflowRun] | None = None,
    workflow_runs_error: bool = False,
) -> FakeHttpClient:
    """Configure FakeHttpClient with REST + GraphQL responses for PlannedPRPlanListService."""
    client = FakeHttpClient()
    endpoint = (
        f"repos/owner/repo/issues?labels={labels}"
        f"&state=open&per_page=30&sort=updated&direction=desc"
    )
    client.set_list_response(endpoint, response=rest_items)
    if pr_numbers:
        client.set_response(
            "graphql",
            response=_make_graphql_enrichment_response(
                pr_numbers,
                is_draft=is_draft,
                checks_state=checks_state,
                review_thread_counts=review_thread_counts,
            ),
        )
    return client


class TestPlannedPRPlanListService:
    """Tests for PlannedPRPlanListService using HTTP-based data fetching."""

    def test_returns_plans_for_planned_prs(self) -> None:
        """Happy path: 1 draft plan PR returns 1 plan."""
        pr_body = "metadata\n\n---\n\n# My Plan\n\nPlan content here"
        rest_items = [_make_rest_item(number=42, title="My Plan", body=pr_body)]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[42])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "42"
        assert result.plans[0].title == "My Plan"

    def test_empty_prs_returns_empty_data(self) -> None:
        """No PRs returns empty plans/linkages/runs."""
        http_client = _setup_planned_pr_http_client(rest_items=[], pr_numbers=[])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_populates_pr_linkages_with_rich_data(self) -> None:
        """pr_linkages contain PullRequestInfo with checks and review thread data."""
        rest_items = [_make_rest_item(number=70, title="Plan", body="body")]
        http_client = _setup_planned_pr_http_client(
            rest_items=rest_items,
            pr_numbers=[70],
            checks_state="SUCCESS",
            review_thread_counts=(1, 2),
        )
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert 70 in result.pr_linkages
        linked_pr = result.pr_linkages[70][0]
        assert linked_pr.checks_passing is True
        assert linked_pr.review_thread_counts == (1, 2)

    def test_created_at_and_author_populated_from_pr_details(self) -> None:
        """Plan created_at and author come from PRDetails."""
        rest_items = [
            _make_rest_item(
                number=90,
                title="Dated Plan",
                body="body",
                author="plan-author",
                created_at="2024-06-15T12:00:00Z",
                updated_at="2024-06-15T12:00:00Z",
            )
        ]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[90])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        plan = result.plans[0]
        assert plan.metadata.get("author") == "plan-author"

    def test_extracts_plan_content_from_body(self) -> None:
        """PR body with metadata separator extracts only plan content."""
        pr_body = (
            "<!-- erk:metadata-block:plan-header -->\n"
            "metadata\n"
            "<!-- /erk:metadata-block -->\n\n---\n\n"
            "# Actual Plan\n\nThe real content"
        )
        rest_items = [_make_rest_item(number=80, title="Plan Title", body=pr_body)]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[80])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert "Actual Plan" in result.plans[0].body
        assert "The real content" in result.plans[0].body
        assert "<!-- erk:metadata-block:" not in result.plans[0].body

    def test_fetches_workflow_runs_from_dispatch_node_id(self) -> None:
        """Draft PR with last_dispatched_node_id in header gets workflow run fetched."""
        pr_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '99999'
last_dispatched_node_id: 'WFR_draft123'
last_dispatched_at: '2024-06-01T10:00:00Z'
```

</details>
<!-- /erk:metadata-block:plan-header -->

---

# Plan content
"""
        run = WorkflowRun(
            run_id="99999",
            status="completed",
            conclusion="success",
            branch="plan-branch",
            head_sha="abc123",
        )
        rest_items = [_make_rest_item(number=100, title="Plan", body=pr_body)]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[100])
        # Set up the second GraphQL call for workflow runs
        # The first graphql call is for PR enrichment; the second is for workflow runs.
        # FakeHttpClient returns the same response for all "graphql" calls,
        # so we need a merged response. Use a dedicated client setup:
        http_client = FakeHttpClient()
        endpoint = (
            "repos/owner/repo/issues?labels=erk-planned-pr,erk-plan"
            "&state=open&per_page=30&sort=updated&direction=desc"
        )
        http_client.set_list_response(endpoint, response=rest_items)
        # graphql responses: the fake returns the same dict for all graphql calls,
        # but enrichment and workflow runs use different keys, so merge them
        enrichment = _make_graphql_enrichment_response([100])
        wf_response = _make_workflow_runs_graphql_response({"WFR_draft123": run})
        merged = {**enrichment, **wf_response}
        merged["data"] = {**enrichment["data"], **wf_response["data"]}
        http_client.set_response("graphql", response=merged)

        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert 100 in result.workflow_runs
        assert result.workflow_runs[100] is not None
        assert result.workflow_runs[100].run_id == "99999"

    def test_skip_workflow_runs_flag_respected(self) -> None:
        """skip_workflow_runs=True skips workflow run fetching."""
        pr_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_draft456'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        rest_items = [_make_rest_item(number=101, title="Plan", body=pr_body)]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[101])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            skip_workflow_runs=True,
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert result.workflow_runs == {}

    def test_rewritten_pr_body_shows_ai_summary_not_footer(self) -> None:
        """Rewritten PR bodies without original-plan section display AI summary content.

        After remote implementation, erk pr rewrite replaces the body with an AI-generated
        summary. These bodies lack the <details>original-plan</details> section, so
        extract_plan_content's fallback returns footer text. The service must detect this
        and use extract_main_content instead.
        """
        # Simulates a rewritten PR body: metadata + separator + AI summary + footer
        pr_body = (
            "<!-- erk:metadata-block:plan-header -->\n"
            "<details>\n<summary><code>plan-header</code></summary>\n\n"
            "```yaml\nschema_version: '2'\n```\n\n"
            "</details>\n"
            "<!-- /erk:metadata-block:plan-header -->\n\n"
            "---\n\n"
            "## Summary\n\n"
            "This PR implements the frobnication feature.\n\n"
            "## Files Changed\n\n"
            "- `src/frob.py`: Added frobnication logic\n\n"
            "## Key Changes\n\n"
            "Rewired the widget to support frobnication"
            "\n---\n"
            "\nCloses #7626\n"
            "\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\n"
            'source "$(erk pr checkout 200 --script)" && erk pr sync --dangerous\n'
            "```\n"
        )
        rest_items = [_make_rest_item(number=200, title="Frobnication", body=pr_body)]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[200])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        plan_body = result.plans[0].body
        # AI summary content should be present
        assert "frobnication feature" in plan_body
        assert "Files Changed" in plan_body
        assert "Key Changes" in plan_body
        # Footer content should NOT be present
        assert "Closes #7626" not in plan_body
        assert "erk pr checkout" not in plan_body

    def test_stage1_pr_body_extracts_original_plan(self) -> None:
        """Stage 1 PR bodies with original-plan section extract plan content correctly.

        Ensures the fix for rewritten bodies doesn't break Stage 1/2 extraction.
        """
        pr_body = (
            "<!-- erk:metadata-block:plan-header -->\n"
            "<details>\n<summary><code>plan-header</code></summary>\n\n"
            "```yaml\nschema_version: '2'\n```\n\n"
            "</details>\n"
            "<!-- /erk:metadata-block:plan-header -->\n\n"
            "---\n\n"
            "<details>\n<summary><code>original-plan</code></summary>\n\n"
            "# My Original Plan\n\nDetailed plan content here"
            "\n\n</details>"
            "\n---\n"
            "\nTo checkout this PR:\n```\nerk pr checkout 201\n```\n"
        )
        rest_items = [_make_rest_item(number=201, title="Stage 1 Plan", body=pr_body)]
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[201])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        plan_body = result.plans[0].body
        assert "My Original Plan" in plan_body
        assert "Detailed plan content here" in plan_body
        # Footer should not leak in
        assert "erk pr checkout 201" not in plan_body

    def test_workflow_run_not_found_returns_none(self) -> None:
        """When node_id exists but workflow run is not found, result maps to None."""
        pr_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_draft789'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        rest_items = [_make_rest_item(number=102, title="Plan", body=pr_body)]
        # Set up client with REST + enrichment; the workflow runs GraphQL call
        # returns the enrichment response (missing "nodes" key), so the node_id
        # is not found — resulting in {102: None}.
        http_client = _setup_planned_pr_http_client(rest_items=rest_items, pr_numbers=[102])
        service = PlannedPRPlanListService(FakeGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-planned-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "102"
        assert 102 in result.workflow_runs
        assert result.workflow_runs[102] is None
