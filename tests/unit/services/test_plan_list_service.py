"""Tests for PlanListService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.types import GitHubRepoId, GitHubRepoLocation, PullRequestInfo, WorkflowRun

from erk.core.services.plan_list_service import PlanListData, PlanListService

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
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues=[issue])

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
        )

        assert len(result.issues) == 1
        assert result.issues[0].number == 42
        assert result.issues[0].title == "Test Plan"
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
            issues=[issue],
            pr_issue_linkages={42: [pr]},
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
        )

        # Unified path returns issues from get_issues_with_pr_linkages
        assert len(result.issues) == 1
        assert result.issues[0].number == 42
        # PR linkages should be fetched together
        assert 42 in result.pr_linkages
        assert result.pr_linkages[42][0].number == 123

    def test_empty_issues_returns_empty_data(self) -> None:
        """Service returns empty data when no issues match."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
        )

        assert result.issues == []
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
        )
        # Configure both issues for the unified query
        fake_github = FakeGitHub(issues=[open_issue, closed_issue])
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
            state="open",
        )

        assert len(result.issues) == 1
        assert result.issues[0].title == "Open Plan"

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
        )
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})
        fake_github = FakeGitHub(issues=[open_issue, closed_issue])

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
            state="closed",
        )

        assert len(result.issues) == 1
        assert result.issues[0].title == "Closed Plan"


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
            issues=[issue],
            workflow_runs_by_node_id={"WFR_abc123": run},
        )

        service = PlanListService(fake_github, fake_issues)
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
            issues=[issue],
            workflow_runs_by_node_id={"WFR_abc123": run},
        )

        service = PlanListService(fake_github, fake_issues)
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
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues=[issue])

        service = PlanListService(fake_github, fake_issues)
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
        )
        # No workflow runs configured - node_id won't be found
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues=[issue])

        service = PlanListService(fake_github, fake_issues)
        result = service.get_plan_list_data(
            location=TEST_LOCATION,
            labels=["erk-plan"],
        )

        # Issue should have None for workflow run (not found)
        assert 42 in result.workflow_runs
        assert result.workflow_runs[42] is None


class TestPlanListData:
    """Tests for PlanListData dataclass."""

    def test_dataclass_is_frozen(self) -> None:
        """PlanListData instances are immutable."""
        data = PlanListData(
            issues=[],
            pr_linkages={},
            workflow_runs={},
        )

        with pytest.raises(AttributeError):
            data.issues = []  # type: ignore[misc]

    def test_dataclass_contains_all_fields(self) -> None:
        """PlanListData has all expected fields."""
        now = datetime.now(UTC)
        issues = [
            IssueInfo(
                number=1,
                title="Plan",
                body="",
                state="OPEN",
                url="",
                labels=[],
                assignees=[],
                created_at=now,
                updated_at=now,
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
            issues=issues,
            pr_linkages=linkages,
            workflow_runs=runs,
        )

        assert data.issues == issues
        assert data.pr_linkages == linkages
        assert data.workflow_runs == runs
