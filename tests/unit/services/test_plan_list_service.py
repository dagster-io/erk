"""Tests for PlanListService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.core.services.plan_list_service import (
    PlanListData,
    PlannedPRPlanListService,
)
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PRDetails,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.types import Plan, PlanState

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
                plan_identifier="1",
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


def _make_planned_pr_details(
    *,
    number: int,
    title: str,
    body: str,
    labels: tuple[str, ...] = ("erk-plan",),
    state: str = "OPEN",
    is_draft: bool = True,
    branch: str = "plan-branch",
) -> PRDetails:
    """Create a PRDetails for testing PlannedPRPlanListService."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body=body,
        state=state,
        is_draft=is_draft,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        labels=labels,
    )


def _make_pr_info(
    *,
    number: int,
    is_draft: bool = True,
    title: str = "Plan",
    branch: str = "plan-branch",
    state: str = "OPEN",
) -> PullRequestInfo:
    """Create a PullRequestInfo for testing PlannedPRPlanListService."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=is_draft,
        title=title,
        checks_passing=None,
        owner="owner",
        repo="repo",
        head_branch=branch,
    )


def _make_plan_pr_data(
    *,
    pr_details_list: list[PRDetails],
) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]]]:
    """Build plan_pr_details tuple for FakeGitHub from a list of PRDetails.

    Creates PullRequestInfo with rich data (checks, review threads) for each PRDetails.
    """
    linkages: dict[int, list[PullRequestInfo]] = {}
    for pr in pr_details_list:
        linkages[pr.number] = [
            PullRequestInfo(
                number=pr.number,
                state=pr.state,
                url=pr.url,
                is_draft=pr.is_draft,
                title=pr.title,
                checks_passing=True,
                owner=pr.owner,
                repo=pr.repo,
                head_branch=pr.head_ref_name,
                review_thread_counts=(0, 0),
            )
        ]
    return (pr_details_list, linkages)


class TestPlannedPRPlanListService:
    """Tests for PlannedPRPlanListService using GraphQL-based data fetching."""

    def test_returns_plans_for_planned_prs(self) -> None:
        """Happy path: 1 draft plan PR returns 1 plan."""
        pr_body = "metadata\n\n---\n\n# My Plan\n\nPlan content here"
        details = _make_planned_pr_details(number=42, title="My Plan", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
        )

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "42"
        assert result.plans[0].title == "My Plan"

    def test_empty_prs_returns_empty_data(self) -> None:
        """No PRs returns empty plans/linkages/runs."""
        fake_github = FakeGitHub()
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
        )

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_populates_pr_linkages_with_rich_data(self) -> None:
        """pr_linkages contain PullRequestInfo with checks and review thread data."""
        details = _make_planned_pr_details(number=70, title="Plan", body="body")
        pr_info = PullRequestInfo(
            number=70,
            state="OPEN",
            url="https://github.com/owner/repo/pull/70",
            is_draft=True,
            title="Plan",
            checks_passing=True,
            owner="owner",
            repo="repo",
            checks_counts=(3, 3),
            review_thread_counts=(1, 2),
            head_branch="plan-branch",
        )
        fake_github = FakeGitHub(
            plan_pr_details=([details], {70: [pr_info]}),
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
        )

        assert len(result.plans) == 1
        assert 70 in result.pr_linkages
        linked_pr = result.pr_linkages[70][0]
        assert linked_pr.checks_passing is True
        assert linked_pr.checks_counts == (3, 3)
        assert linked_pr.review_thread_counts == (1, 2)

    def test_created_at_and_author_populated_from_pr_details(self) -> None:
        """Plan created_at and author come from PRDetails."""
        pr_created_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        details = PRDetails(
            number=90,
            url="https://github.com/owner/repo/pull/90",
            title="Dated Plan",
            body="body",
            state="OPEN",
            is_draft=True,
            base_ref_name="main",
            head_ref_name="dated-branch",
            is_cross_repository=False,
            mergeable="UNKNOWN",
            merge_state_status="UNKNOWN",
            owner="owner",
            repo="repo",
            labels=("erk-plan",),
            created_at=pr_created_at,
            updated_at=pr_created_at,
            author="plan-author",
        )
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
        )

        assert len(result.plans) == 1
        plan = result.plans[0]
        assert plan.created_at == pr_created_at
        assert plan.metadata.get("author") == "plan-author"

    def test_extracts_plan_content_from_body(self) -> None:
        """PR body with metadata separator extracts only plan content."""
        pr_body = (
            "<!-- erk:metadata-block:plan-header -->\n"
            "metadata\n"
            "<!-- /erk:metadata-block -->\n\n---\n\n"
            "# Actual Plan\n\nThe real content"
        )
        details = _make_planned_pr_details(number=80, title="Plan Title", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
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
        details = _make_planned_pr_details(number=100, title="Plan", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
            workflow_runs_by_node_id={"WFR_draft123": run},
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
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
        run = WorkflowRun(
            run_id="12345",
            status="completed",
            conclusion="success",
            branch="plan-branch",
            head_sha="abc",
        )
        details = _make_planned_pr_details(number=101, title="Plan", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
            workflow_runs_by_node_id={"WFR_draft456": run},
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            skip_workflow_runs=True,
            http_client=None,
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
        details = _make_planned_pr_details(number=200, title="Frobnication", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
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
        details = _make_planned_pr_details(number=201, title="Stage 1 Plan", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
        )

        assert len(result.plans) == 1
        plan_body = result.plans[0].body
        assert "My Original Plan" in plan_body
        assert "Detailed plan content here" in plan_body
        # Footer should not leak in
        assert "erk pr checkout 201" not in plan_body

    def test_workflow_run_api_failure_returns_empty_runs(self) -> None:
        """API failure during workflow run fetch still returns plans with empty runs."""
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
        details = _make_planned_pr_details(number=102, title="Plan", body=pr_body)
        fake_github = FakeGitHub(
            plan_pr_details=_make_plan_pr_data(pr_details_list=[details]),
            workflow_runs_error="Network unreachable",
        )
        service = PlannedPRPlanListService(fake_github, time=FakeTime())
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-pr", "erk-plan"],
            http_client=None,
        )

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "102"
        assert result.workflow_runs == {}
