"""Unit tests for add-plan-labels batch command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.add_plan_labels import add_plan_labels
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.time import FakeTime
from tests.test_utils.plan_helpers import issue_info_to_pr_details


def _make_issue(
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create a test IssueInfo."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_add_plan_labels_batch_success() -> None:
    """Test successfully adding labels to multiple plans."""
    issue_42 = _make_issue(42, "Plan A", "Body A")
    issue_43 = _make_issue(43, "Plan B", "Body B")
    fake_gh = FakeGitHubIssues(issues={42: issue_42, 43: issue_43})
    fake_github = FakeLocalGitHub(
        pr_details={
            42: issue_info_to_pr_details(issue_42),
            43: issue_info_to_pr_details(issue_43),
        },
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    batch_input = json.dumps(
        [
            {"pr_number": 42, "label": "erk-learn"},
            {"pr_number": 43, "label": "erk-stale"},
        ]
    )

    result = runner.invoke(
        add_plan_labels,
        input=batch_input,
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 2
    assert output["results"][0]["pr_number"] == 42
    assert output["results"][0]["success"] is True
    assert output["results"][0]["label"] == "erk-learn"
    assert output["results"][1]["pr_number"] == 43
    assert output["results"][1]["success"] is True


def test_add_plan_labels_partial_failure() -> None:
    """Test batch where one plan fails but others succeed."""
    issue_42 = _make_issue(42, "Plan A", "Body A")
    fake_gh = FakeGitHubIssues(issues={42: issue_42})
    fake_github = FakeLocalGitHub(
        pr_details={42: issue_info_to_pr_details(issue_42)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    batch_input = json.dumps(
        [
            {"pr_number": 42, "label": "erk-learn"},
            {"pr_number": 999, "label": "erk-stale"},
        ]
    )

    result = runner.invoke(
        add_plan_labels,
        input=batch_input,
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert len(output["results"]) == 2
    assert output["results"][0]["success"] is True
    assert output["results"][1]["success"] is False


def test_add_plan_labels_invalid_json() -> None:
    """Test error handling for invalid JSON input."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        add_plan_labels,
        input="not valid json",
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-json"


def test_add_plan_labels_missing_field() -> None:
    """Test error handling for missing required fields."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    batch_input = json.dumps([{"pr_number": 42}])  # Missing 'label'

    result = runner.invoke(
        add_plan_labels,
        input=batch_input,
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "label" in output["message"]


def test_add_plan_labels_empty_array() -> None:
    """Test that empty array returns success with no results."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        add_plan_labels,
        input="[]",
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["results"] == []
