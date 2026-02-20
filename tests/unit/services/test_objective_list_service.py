"""Tests for ObjectiveListService."""

from datetime import UTC, datetime
from pathlib import Path

from erk.core.services.objective_list_service import RealObjectiveListService
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation

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
        fake_issues = FakeGitHubIssues(issues={10: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealObjectiveListService(fake_github, fake_issues)
        result = service.get_objective_list_data(location=TEST_LOCATION)

        assert len(result.plans) == 1
        assert result.plans[0].plan_identifier == "10"
        assert result.plans[0].title == "Test Objective"

    def test_forwards_state_parameter(self) -> None:
        """Verify state parameter passes through to underlying service."""
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
        fake_github = FakeGitHub(issues_data=[open_issue, closed_issue])
        fake_issues = FakeGitHubIssues(issues={1: open_issue, 2: closed_issue})

        service = RealObjectiveListService(fake_github, fake_issues)
        result = service.get_objective_list_data(location=TEST_LOCATION, state="open")

        assert len(result.plans) == 1
        assert result.plans[0].title == "Open Objective"

    def test_forwards_limit_parameter(self) -> None:
        """Verify limit parameter passes through to underlying service."""
        now = datetime.now(UTC)
        issues = []
        issues_dict = {}
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
            issues_dict[i + 1] = issue
        fake_github = FakeGitHub(issues_data=issues)
        fake_issues = FakeGitHubIssues(issues=issues_dict)

        service = RealObjectiveListService(fake_github, fake_issues)
        result = service.get_objective_list_data(location=TEST_LOCATION, limit=2)

        assert len(result.plans) <= 2

    def test_forwards_skip_workflow_runs(self) -> None:
        """Verify skip_workflow_runs passes through to underlying service."""
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
        fake_issues = FakeGitHubIssues(issues={42: issue})
        fake_github = FakeGitHub(issues_data=[issue])

        service = RealObjectiveListService(fake_github, fake_issues)
        result = service.get_objective_list_data(location=TEST_LOCATION, skip_workflow_runs=True)

        assert result.workflow_runs == {}

    def test_forwards_creator_parameter(self) -> None:
        """Verify creator parameter passes through to underlying service."""
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
        fake_github = FakeGitHub(issues_data=[issue_alice, issue_bob])
        fake_issues = FakeGitHubIssues(issues={1: issue_alice, 2: issue_bob})

        service = RealObjectiveListService(fake_github, fake_issues)
        result = service.get_objective_list_data(location=TEST_LOCATION, creator="alice")

        assert len(result.plans) == 1
        assert result.plans[0].title == "Alice Objective"

    def test_returns_empty_data_when_no_objectives(self) -> None:
        """Empty case returns empty data."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeGitHub()

        service = RealObjectiveListService(fake_github, fake_issues)
        result = service.get_objective_list_data(location=TEST_LOCATION)

        assert result.plans == []
        assert result.pr_linkages == {}
        assert result.workflow_runs == {}
