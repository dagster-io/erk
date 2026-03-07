"""Tests for ObjectiveListService."""

from datetime import UTC, datetime
from pathlib import Path

from erk.core.services.objective_list_service import RealObjectiveListService
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation, WorkflowRun
from erk_shared.gateway.http.fake import FakeHttpClient
from erk_shared.gateway.time.fake import FakeTime

TEST_LOCATION = GitHubRepoLocation(root=Path("/test/repo"), repo_id=GitHubRepoId("owner", "repo"))


class TestObjectiveListService:
    """Tests for RealObjectiveListService with injected fakes."""

    def test_fetches_objectives_with_hardcoded_label(self) -> None:
        """Verify issues with erk-objective label are returned."""
        now = datetime.now(UTC)
        issue = IssueInfo(
            number=10,
            title="Test Objective",
            body="Objective body",
            state="OPEN",
            url="https://github.com/owner/repo/issues/10",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_github = FakeLocalGitHub(issues_data=[issue])

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, http_client=FakeHttpClient()
        )

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "10"
        assert result.plans[0].title == "Test Objective"

    def test_forwards_state_parameter(self) -> None:
        """Verify state parameter passes through."""
        now = datetime.now(UTC)
        open_issue = IssueInfo(
            number=1,
            title="Open Objective",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/1",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        closed_issue = IssueInfo(
            number=2,
            title="Closed Objective",
            body="",
            state="CLOSED",
            url="https://github.com/owner/repo/issues/2",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_github = FakeLocalGitHub(issues_data=[open_issue, closed_issue])

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, state="open", http_client=FakeHttpClient()
        )

        assert len(result.plans) == 1
        assert result.plans[0].title == "Open Objective"

    def test_forwards_limit_parameter(self) -> None:
        """Verify limit parameter passes through."""
        now = datetime.now(UTC)
        issues = []
        for i in range(5):
            issue = IssueInfo(
                number=i + 1,
                title=f"Objective {i + 1}",
                body="",
                state="OPEN",
                url=f"https://github.com/owner/repo/issues/{i + 1}",
                labels=["erk-objective"],
                assignees=[],
                created_at=now,
                updated_at=now,
                author="test-user",
            )
            issues.append(issue)
        fake_github = FakeLocalGitHub(issues_data=issues)

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, limit=2, http_client=FakeHttpClient()
        )

        assert len(result.plans) <= 2

    def test_forwards_skip_workflow_runs(self) -> None:
        """Verify skip_workflow_runs=True skips workflow run fetching."""
        now = datetime.now(UTC)
        issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_obj123'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        issue = IssueInfo(
            number=42,
            title="Test Objective",
            body=issue_body,
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        fake_github = FakeLocalGitHub(issues_data=[issue])

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, skip_workflow_runs=True, http_client=FakeHttpClient()
        )

        assert result.workflow_runs == {}

    def test_fetches_workflow_runs_when_not_skipped(self) -> None:
        """Verify workflow runs are fetched when skip_workflow_runs is False."""
        now = datetime.now(UTC)
        issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_node_id: 'WFR_obj456'
```

</details>
<!-- /erk:metadata-block:plan-header -->
"""
        issue = IssueInfo(
            number=42,
            title="Test Objective",
            body=issue_body,
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="test-user",
        )
        run = WorkflowRun(
            run_id="99999",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc123",
        )
        fake_github = FakeLocalGitHub(
            issues_data=[issue],
            workflow_runs_by_node_id={"WFR_obj456": run},
        )

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, http_client=FakeHttpClient()
        )

        assert 42 in result.workflow_runs
        assert result.workflow_runs[42] is not None
        assert result.workflow_runs[42].run_id == "99999"

    def test_forwards_creator_parameter(self) -> None:
        """Verify creator parameter passes through."""
        now = datetime.now(UTC)
        issue_alice = IssueInfo(
            number=1,
            title="Alice Objective",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/1",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="alice",
        )
        issue_bob = IssueInfo(
            number=2,
            title="Bob Objective",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/2",
            labels=["erk-objective"],
            assignees=[],
            created_at=now,
            updated_at=now,
            author="bob",
        )
        fake_github = FakeLocalGitHub(issues_data=[issue_alice, issue_bob])

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, creator="alice", http_client=FakeHttpClient()
        )

        assert len(result.plans) == 1
        assert result.plans[0].title == "Alice Objective"

    def test_returns_empty_data_when_no_objectives(self) -> None:
        """Empty case returns empty data."""
        fake_github = FakeLocalGitHub()

        service = RealObjectiveListService(fake_github, time=FakeTime())
        result = service.get_objective_list_data(
            location=TEST_LOCATION, http_client=FakeHttpClient()
        )

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}
