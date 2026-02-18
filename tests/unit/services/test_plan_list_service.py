"""Tests for PlanListService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.core.services.plan_list_service import (
    DraftPRPlanListService,
    PlanListData,
    RealPlanListService,
)
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PRDetails,
    PullRequestInfo,
    WorkflowRun,
)
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
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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
            labels=["erk-plan"],
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

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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
            labels=["erk-plan"],
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
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        # Configure both issues for the unified query
        fake_github = FakeGitHub(issues_data=[open_issue, closed_issue])
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
            state="open",
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
            labels=["erk-plan"],
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
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})
        fake_github = FakeGitHub(issues_data=[open_issue, closed_issue])

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
            state="closed",
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
            labels=["erk-plan"],
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

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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
            labels=["erk-plan"],
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

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
            skip_workflow_runs=True,
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
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        # No workflow runs configured - node_id won't be found
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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
            labels=["erk-plan"],
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

        service = RealPlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
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
                labels=[],
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
        )

        assert data.plans == plans
        assert data.pr_linkages == linkages
        assert data.workflow_runs == runs


def _make_draft_pr_details(
    *,
    number: int,
    title: str,
    body: str,
    labels: tuple[str, ...] = ("erk-plan",),
    state: str = "OPEN",
    is_draft: bool = True,
    branch: str = "plan-branch",
) -> PRDetails:
    """Create a PRDetails for testing DraftPRPlanListService."""
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
    """Create a PullRequestInfo for testing DraftPRPlanListService."""
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


class TestDraftPRPlanListService:
    """Tests for DraftPRPlanListService."""

    def test_returns_plans_for_draft_prs_with_erk_plan_label(self) -> None:
        """Happy path: 1 draft plan PR returns 1 plan."""
        pr_body = "metadata\n\n---\n\n# My Plan\n\nPlan content here"
        fake_github = FakeGitHub(
            prs={"plan-branch": _make_pr_info(number=42)},
            pr_details={42: _make_draft_pr_details(number=42, title="My Plan", body=pr_body)},
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "42"
        assert result.plans[0].title == "My Plan"

    def test_filters_out_non_draft_prs(self) -> None:
        """Non-draft PRs with erk-plan label are excluded."""
        fake_github = FakeGitHub(
            prs={"feature": _make_pr_info(number=10, is_draft=False, branch="feature")},
            pr_details={
                10: _make_draft_pr_details(
                    number=10, title="Not Draft", body="body", is_draft=False, branch="feature"
                )
            },
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert result.plans == []

    def test_filters_out_prs_without_erk_plan_label(self) -> None:
        """Draft PRs without erk-plan label are excluded."""
        fake_github = FakeGitHub(
            prs={"draft-no-label": _make_pr_info(number=20, branch="draft-no-label")},
            pr_details={
                20: _make_draft_pr_details(
                    number=20, title="No Label", body="body", labels=(), branch="draft-no-label"
                )
            },
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert result.plans == []

    def test_applies_additional_label_filters(self) -> None:
        """labels=["erk-learn"] requires ALL labels present."""
        fake_github = FakeGitHub(
            prs={
                "has-both": _make_pr_info(number=30, branch="has-both"),
                "only-plan": _make_pr_info(number=31, branch="only-plan"),
            },
            pr_details={
                30: _make_draft_pr_details(
                    number=30,
                    title="Both Labels",
                    body="body",
                    labels=("erk-plan", "erk-learn"),
                    branch="has-both",
                ),
                31: _make_draft_pr_details(
                    number=31,
                    title="Only Plan",
                    body="body",
                    labels=("erk-plan",),
                    branch="only-plan",
                ),
            },
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=["erk-learn"])

        assert len(result.plans) == 1
        assert result.plans[0].title == "Both Labels"

    def test_state_filtering(self) -> None:
        """state="closed" passes through to list_prs."""
        fake_github = FakeGitHub(
            prs={
                "closed-plan": _make_pr_info(number=40, branch="closed-plan", state="CLOSED"),
            },
            pr_details={
                40: _make_draft_pr_details(
                    number=40,
                    title="Closed Plan",
                    body="body",
                    state="CLOSED",
                    branch="closed-plan",
                )
            },
        )
        service = DraftPRPlanListService(fake_github)

        # With state="open" the closed PR should not appear
        result_open = service.get_plan_list_data(location=TEST_LOCATION, labels=[], state="open")
        assert result_open.plans == []

        # With state="closed" it should appear
        result_closed = service.get_plan_list_data(
            location=TEST_LOCATION, labels=[], state="closed"
        )
        assert len(result_closed.plans) == 1
        assert result_closed.plans[0].title == "Closed Plan"

    def test_respects_limit(self) -> None:
        """limit=2 returns exactly 2 from 3 PRs."""
        prs: dict[str, PullRequestInfo] = {}
        pr_details: dict[int, PRDetails] = {}
        for i in range(3):
            branch = f"plan-{i}"
            number = 50 + i
            prs[branch] = _make_pr_info(number=number, branch=branch, title=f"Plan {i}")
            pr_details[number] = _make_draft_pr_details(
                number=number, title=f"Plan {i}", body="body", branch=branch
            )

        fake_github = FakeGitHub(prs=prs, pr_details=pr_details)
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[], limit=2)

        assert len(result.plans) == 2

    def test_handles_pr_not_found(self) -> None:
        """PR in list_prs but missing from pr_details is skipped."""
        fake_github = FakeGitHub(
            prs={"orphan": _make_pr_info(number=60, branch="orphan")},
            # Intentionally no pr_details for 60
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert result.plans == []

    def test_empty_prs_returns_empty_data(self) -> None:
        """No PRs returns empty plans/linkages/runs."""
        fake_github = FakeGitHub()
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_always_returns_empty_pr_linkages_and_workflow_runs(self) -> None:
        """pr_linkages and workflow_runs are always empty for draft PRs."""
        fake_github = FakeGitHub(
            prs={"plan": _make_pr_info(number=70)},
            pr_details={70: _make_draft_pr_details(number=70, title="Plan", body="body")},
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert len(result.plans) == 1
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}

    def test_extracts_plan_content_from_body(self) -> None:
        """PR body with metadata separator extracts only plan content."""
        pr_body = "<!-- metadata -->\n\n---\n\n# Actual Plan\n\nThe real content"
        fake_github = FakeGitHub(
            prs={"content-plan": _make_pr_info(number=80, branch="content-plan")},
            pr_details={
                80: _make_draft_pr_details(
                    number=80, title="Plan Title", body=pr_body, branch="content-plan"
                )
            },
        )
        service = DraftPRPlanListService(fake_github)
        result = service.get_plan_list_data(location=TEST_LOCATION, labels=[])

        assert len(result.plans) == 1
        # The body should be the extracted plan content (after the separator)
        assert "Actual Plan" in result.plans[0].body
        assert "The real content" in result.plans[0].body
        # Metadata portion should not be in the plan body
        assert "<!-- metadata -->" not in result.plans[0].body
