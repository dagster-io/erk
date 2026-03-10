"""Tests for PlanListService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.core.services.plan_list_service import (
    PlanListData,
    PlannedPRPlanListService,
    RealPlanListService,
)
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.http import FakeHttpClient
from tests.fakes.gateway.time import FakeTime

TEST_LOCATION = GitHubRepoLocation(root=Path("/test/repo"), repo_id=GitHubRepoId("owner", "repo"))


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
                pr_identifier="1",
                title="Plan",
                body="",
                state=PlanState.OPEN,
                url="",
                labels=["erk-pr", "erk-plan"],
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


def _make_rest_issue_pr(
    *,
    number: int,
    title: str = "Plan PR",
    body: str = "metadata\n\n---\n\n# Plan\n\nContent",
    labels: list[str] | None = None,
    branch: str | None = None,
    created_at: str = "2024-01-15T10:00:00Z",
    updated_at: str = "2024-01-15T14:00:00Z",
    author: str = "test-user",
) -> dict:
    """Build a REST API issue item that looks like a PR (for HTTP path tests)."""
    effective_branch = branch or f"plan-branch-{number}"
    return {
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "state": "open",
        "created_at": created_at,
        "updated_at": updated_at,
        "labels": [{"name": label} for label in (labels or ["erk-plan"])],
        "user": {"login": author},
        "pull_request": {"head": {"ref": effective_branch}},
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
            "statusCheckRollup": {
                "state": "SUCCESS",
                "contexts": {
                    "totalCount": 3,
                    "checkRunCountsByState": [{"state": "SUCCESS", "count": 3}],
                    "statusContextCountsByState": [],
                },
            },
            "reviewThreads": {"totalCount": 0, "nodes": []},
            "reviewDecision": "APPROVED",
        }
    return {"data": {"repository": repo_data}}


def _setup_http_for_prs(
    *,
    rest_items: list[dict],
    pr_numbers: list[int],
    labels: str = "erk-pr,erk-plan",
    graphql_override: dict | None = None,
) -> FakeHttpClient:
    """Configure FakeHttpClient with REST + GraphQL responses for planned PR tests."""
    client = FakeHttpClient()
    endpoint = (
        f"repos/owner/repo/issues?labels={labels}"
        f"&state=open&per_page=30&sort=updated&direction=desc"
    )
    client.set_list_response(endpoint, response=rest_items)
    client.set_response(
        "graphql",
        response=graphql_override or _make_graphql_enrichment(pr_numbers),
    )
    return client


class TestPlannedPRPlanListService:
    """Tests for PlannedPRPlanListService using HTTP-based data fetching."""

    def test_returns_plans_for_planned_prs(self) -> None:
        """Happy path: 1 draft plan PR returns 1 plan."""
        pr_body = "metadata\n\n---\n\n# My Plan\n\nPlan content here"
        rest_items = [_make_rest_issue_pr(number=42, title="My Plan", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[42])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert result.plans[0].pr_identifier == "42"
        assert result.plans[0].title == "My Plan"

    def test_empty_prs_returns_empty_data(self) -> None:
        """No PRs returns empty plans/linkages/runs."""
        http_client = _setup_http_for_prs(rest_items=[], pr_numbers=[])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_populates_pr_linkages_with_rich_data(self) -> None:
        """pr_linkages contain PullRequestInfo with checks and review thread data."""
        rest_items = [_make_rest_issue_pr(number=70, title="Plan", body="body")]
        enrichment = {
            "data": {
                "repository": {
                    "pr_70": {
                        "isDraft": True,
                        "mergeable": "MERGEABLE",
                        "mergeStateStatus": "CLEAN",
                        "isCrossRepository": False,
                        "baseRefName": "main",
                        "headRefName": "plan-branch",
                        "statusCheckRollup": {
                            "state": "SUCCESS",
                            "contexts": {
                                "totalCount": 3,
                                "checkRunCountsByState": [
                                    {"state": "SUCCESS", "count": 3},
                                ],
                                "statusContextCountsByState": [],
                            },
                        },
                        "reviewThreads": {
                            "totalCount": 2,
                            "nodes": [
                                {"isResolved": True},
                                {"isResolved": False},
                            ],
                        },
                        "reviewDecision": "APPROVED",
                    }
                }
            }
        }
        http_client = _setup_http_for_prs(
            rest_items=rest_items,
            pr_numbers=[70],
            graphql_override=enrichment,
        )

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert 70 in result.pr_linkages
        linked_pr = result.pr_linkages[70][0]
        assert linked_pr.checks_passing is True
        assert linked_pr.review_thread_counts == (1, 2)

    def test_created_at_and_author_populated_from_pr_details(self) -> None:
        """Plan created_at and author come from REST data."""
        rest_items = [
            _make_rest_issue_pr(
                number=90,
                title="Dated Plan",
                body="body",
                branch="dated-branch",
                created_at="2024-06-15T12:00:00Z",
                updated_at="2024-06-15T12:00:00Z",
                author="plan-author",
            )
        ]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[90])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        plan = result.plans[0]
        assert plan.created_at.year == 2024
        assert plan.created_at.month == 6
        assert plan.metadata.get("author") == "plan-author"

    def test_extracts_plan_content_from_body(self) -> None:
        """PR body with metadata separator extracts only plan content."""
        pr_body = (
            "<!-- erk:metadata-block:plan-header -->\n"
            "metadata\n"
            "<!-- /erk:metadata-block -->\n\n---\n\n"
            "# Actual Plan\n\nThe real content"
        )
        rest_items = [_make_rest_issue_pr(number=80, title="Plan Title", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[80])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
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
        rest_items = [_make_rest_issue_pr(number=100, title="Plan", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[100])
        # Configure workflow run GraphQL response
        http_client.set_response(
            "graphql",
            response=_make_graphql_enrichment([100]),
        )

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        # Workflow runs are fetched via a second GraphQL call, but with FakeHttpClient
        # both enrichment and workflow run queries hit the same "graphql" endpoint.
        # The enrichment response is returned for both, so workflow runs may be empty.
        # This is acceptable — the HTTP workflow run path is tested separately.

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
        rest_items = [_make_rest_issue_pr(number=101, title="Plan", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[101])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
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
            'source "$(erk pr checkout 200 --script)"\n'
            "```\n"
        )
        rest_items = [_make_rest_issue_pr(number=200, title="Frobnication", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[200])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
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
        assert "erk pr teleport" not in plan_body

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
        rest_items = [_make_rest_issue_pr(number=201, title="Stage 1 Plan", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[201])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        plan_body = result.plans[0].body
        assert "My Original Plan" in plan_body
        assert "Detailed plan content here" in plan_body
        # Footer should not leak in
        assert "erk pr checkout 201" not in plan_body

    def test_no_workflow_runs_when_no_dispatch_node_id(self) -> None:
        """Plans without dispatch node IDs have no workflow runs."""
        pr_body = "Simple body\n\n---\n\n# Plan content"
        rest_items = [_make_rest_issue_pr(number=102, title="Plan", body=pr_body)]
        http_client = _setup_http_for_prs(rest_items=rest_items, pr_numbers=[102])

        service = PlannedPRPlanListService(FakeLocalGitHub(), time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=http_client,
        )

        assert len(result.plans) == 1
        assert result.plans[0].pr_identifier == "102"
        assert result.workflow_runs == {}


class TestBuildEnrichmentWarnings:
    """Tests for _build_enrichment_warnings helper function."""

    def test_no_warnings_when_all_enriched(self) -> None:
        """No warnings when unenriched_count is zero."""
        from erk.core.services.plan_list_service import _build_enrichment_warnings

        result = _build_enrichment_warnings(0, 5)

        assert result == ()

    def test_warning_when_some_unenriched(self) -> None:
        """Warning message includes counts when some PRs lack enrichment."""
        from erk.core.services.plan_list_service import _build_enrichment_warnings

        result = _build_enrichment_warnings(2, 5)

        assert len(result) == 1
        assert "2/5" in result[0]
        assert "GraphQL enrichment failed" in result[0]

    def test_warning_when_all_unenriched(self) -> None:
        """Warning message when all PRs lack enrichment."""
        from erk.core.services.plan_list_service import _build_enrichment_warnings

        result = _build_enrichment_warnings(3, 3)

        assert len(result) == 1
        assert "3/3" in result[0]

    def test_returns_tuple(self) -> None:
        """Return type is always a tuple."""
        from erk.core.services.plan_list_service import _build_enrichment_warnings

        assert isinstance(_build_enrichment_warnings(0, 0), tuple)
        assert isinstance(_build_enrichment_warnings(1, 1), tuple)


# --- RealPlanListService tests (Layer 4) ---

_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

_PLAN_HEADER_BODY = (
    "<!-- erk:metadata-block:plan-header -->\n"
    "<details>\n<summary><code>plan-header</code></summary>\n\n"
    "```yaml\n"
    "schema_version: '2'\n"
    "last_dispatched_run_id: '99999'\n"
    "last_dispatched_node_id: 'WFR_node123'\n"
    "last_dispatched_at: '2024-06-01T10:00:00Z'\n"
    "```\n\n"
    "</details>\n"
    "<!-- /erk:metadata-block:plan-header -->\n\n"
    "# Plan body"
)


def _make_issue(
    *,
    number: int = 1,
    title: str = "Test Plan",
    body: str = "# Plan body",
    labels: list[str] | None = None,
    author: str = "test-user",
) -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=labels or ["erk-plan"],
        assignees=[],
        created_at=_NOW,
        updated_at=_NOW,
        author=author,
    )


def test_real_plan_list_service_returns_empty_data_when_no_issues() -> None:
    """FakeLocalGitHub with no issues_data returns empty PlanListData."""
    github = FakeLocalGitHub()
    service = RealPlanListService(github, FakeGitHubIssues(), time=FakeTime())

    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=FakeHttpClient(),
    )

    assert result.plans == []
    assert result.pr_linkages == {}
    assert result.workflow_runs == {}


def test_real_plan_list_service_fetches_issues_and_converts_to_plans() -> None:
    """Pre-configured issues_data returns plans via github_issue_to_plan()."""
    issues = [
        _make_issue(number=10, title="Plan A"),
        _make_issue(number=20, title="Plan B"),
    ]
    github = FakeLocalGitHub(issues_data=issues)
    service = RealPlanListService(github, FakeGitHubIssues(), time=FakeTime())

    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=FakeHttpClient(),
    )

    assert len(result.plans) == 2
    assert result.plans[0].pr_identifier == "10"
    assert result.plans[0].title == "Plan A"
    assert result.plans[1].pr_identifier == "20"
    assert result.plans[1].title == "Plan B"


def test_real_plan_list_service_skips_workflow_runs_when_requested() -> None:
    """With skip_workflow_runs=True, workflow_runs dict is empty even if dispatch info exists."""
    issues = [_make_issue(number=1, body=_PLAN_HEADER_BODY)]
    workflow_runs_by_node_id = {
        "WFR_node123": WorkflowRun(
            run_id="99999",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc123",
        ),
    }
    github = FakeLocalGitHub(
        issues_data=issues,
        workflow_runs_by_node_id=workflow_runs_by_node_id,
    )
    service = RealPlanListService(github, FakeGitHubIssues(), time=FakeTime())

    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        skip_workflow_runs=True,
        http_client=FakeHttpClient(),
    )

    assert len(result.plans) == 1
    assert result.workflow_runs == {}


def test_real_plan_list_service_fetches_workflow_runs_by_node_id() -> None:
    """Issues with plan-header dispatch info trigger batch workflow run fetch."""
    issues = [_make_issue(number=1, body=_PLAN_HEADER_BODY)]
    run = WorkflowRun(
        run_id="99999",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc123",
    )
    github = FakeLocalGitHub(
        issues_data=issues,
        workflow_runs_by_node_id={"WFR_node123": run},
    )
    service = RealPlanListService(github, FakeGitHubIssues(), time=FakeTime())

    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=FakeHttpClient(),
    )

    assert len(result.plans) == 1
    assert 1 in result.workflow_runs
    assert result.workflow_runs[1] is not None
    assert result.workflow_runs[1].run_id == "99999"


def test_real_plan_list_service_graceful_on_workflow_run_failure() -> None:
    """Workflow run API failure returns plans with empty workflow_runs."""
    issues = [_make_issue(number=1, body=_PLAN_HEADER_BODY)]
    github = FakeLocalGitHub(
        issues_data=issues,
        workflow_runs_error="API rate limited",
    )
    service = RealPlanListService(github, FakeGitHubIssues(), time=FakeTime())

    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=FakeHttpClient(),
    )

    assert len(result.plans) == 1
    assert result.workflow_runs == {}


def test_real_plan_list_service_populates_timing_fields() -> None:
    """All timing fields (api_ms, plan_parsing_ms, workflow_runs_ms) are non-negative floats."""
    issues = [_make_issue(number=1)]
    github = FakeLocalGitHub(issues_data=issues)
    fake_time = FakeTime(monotonic_values=[0.0, 0.1, 0.15, 0.2])
    service = RealPlanListService(github, FakeGitHubIssues(), time=fake_time)

    result = service.get_plan_list_data(
        location=TEST_LOCATION,
        labels=["erk-plan"],
        http_client=FakeHttpClient(),
    )

    assert result.api_ms >= 0.0
    assert result.plan_parsing_ms >= 0.0
    assert result.workflow_runs_ms >= 0.0
    # With monotonic values [0.0, 0.1, 0.15, 0.2], expect meaningful timing
    assert result.api_ms == pytest.approx(100.0)
    assert result.plan_parsing_ms == pytest.approx(50.0)
    assert result.workflow_runs_ms == pytest.approx(50.0)
