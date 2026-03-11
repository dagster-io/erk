"""Unit tests for close-prs batch command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.close_prs import close_prs
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.planned_pr import GitHubManagedPrBackend
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
        labels=["erk-pr"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_close_prs_batch_success() -> None:
    """Test successfully closing multiple plans in a batch."""
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
            {"pr_number": 42, "comment": "Closing plan A"},
            {"pr_number": 43, "comment": "Closing plan B"},
        ]
    )

    result = runner.invoke(
        close_prs,
        input=batch_input,
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=GitHubManagedPrBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 2
    assert output["results"][0]["pr_number"] == 42
    assert output["results"][0]["success"] is True
    assert output["results"][1]["pr_number"] == 43
    assert output["results"][1]["success"] is True

    # Verify both PRs were closed
    assert 42 in fake_github.closed_prs
    assert 43 in fake_github.closed_prs


def test_close_prs_partial_failure() -> None:
    """Test batch where one plan fails (not found) but others succeed."""
    issue_42 = _make_issue(42, "Plan A", "Body A")
    fake_gh = FakeGitHubIssues(issues={42: issue_42})
    fake_github = FakeLocalGitHub(
        pr_details={42: issue_info_to_pr_details(issue_42)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    batch_input = json.dumps(
        [
            {"pr_number": 42, "comment": "Closing plan A"},
            {"pr_number": 999, "comment": "This should fail"},
        ]
    )

    result = runner.invoke(
        close_prs,
        input=batch_input,
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=GitHubManagedPrBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False  # Overall failure due to one failing
    assert len(output["results"]) == 2
    assert output["results"][0]["success"] is True
    assert output["results"][1]["success"] is False
    assert "999" in str(output["results"][1].get("error", ""))


def test_close_prs_invalid_json() -> None:
    """Test error handling for invalid JSON input."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        close_prs,
        input="not valid json",
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=GitHubManagedPrBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-json"


def test_close_prs_missing_field() -> None:
    """Test error handling for missing required fields."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    batch_input = json.dumps([{"pr_number": 42}])  # Missing 'comment'

    result = runner.invoke(
        close_prs,
        input=batch_input,
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=GitHubManagedPrBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "comment" in output["message"]


def test_close_prs_empty_array() -> None:
    """Test that empty array returns success with no results."""
    fake_gh = FakeGitHubIssues()
    fake_github = FakeLocalGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        close_prs,
        input="[]",
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=GitHubManagedPrBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["results"] == []
