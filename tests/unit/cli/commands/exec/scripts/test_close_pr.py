"""Unit tests for close-pr command.

Tests use PlannedPRBackend for dependency injection via ErkContext.for_test().
The command uses PlanBackend which routes to FakeGitHub PR operations.
"""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.close_pr import (
    close_pr,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
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


def test_close_pr_success() -> None:
    """Test successfully closing an issue with a comment."""
    issue = _make_issue(42, "Test Issue", "This is the issue body")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(
        pr_details={42: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    result = runner.invoke(
        close_pr,
        ["42", "--comment", "Closing: work is done."],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == 42
    # PlannedPRBackend.add_comment returns string ID from FakeGitHub (starts at 1000000)
    assert output["comment_id"] == "1000000"

    # Verify the user comment was added (via PlannedPRBackend -> FakeGitHub.create_pr_comment)
    assert len(fake_github.pr_comments) >= 1
    # First PR comment is the user's comment
    pr_number, comment_body = fake_github.pr_comments[0]
    assert pr_number == 42
    assert comment_body == "Closing: work is done."

    # Verify the PR was closed (close_plan adds its own audit comment + closes PR)
    assert 42 in fake_github.closed_prs


def test_close_pr_not_found() -> None:
    """Test error when issue does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty issues dict
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        close_pr,
        ["999", "--comment", "This should fail"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]

    # Verify no mutations occurred
    assert len(fake_github.pr_comments) == 0
    assert len(fake_github.closed_prs) == 0


def test_close_pr_multiline() -> None:
    """Test closing with a multiline comment."""
    issue = _make_issue(100, "Plan Issue", "Implementation plan")
    fake_gh = FakeGitHubIssues(issues={100: issue})
    fake_github = FakeGitHub(
        pr_details={100: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    multiline_comment = """Closing as superseded.

## Evidence
- Work merged in PR #1234
- Feature exists at src/foo.py

See #1234 for details."""

    result = runner.invoke(
        close_pr,
        ["100", "--comment", multiline_comment],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == 100

    # Verify the full comment was preserved (via FakeGitHub.create_pr_comment)
    pr_number, comment_body = fake_github.pr_comments[0]
    assert pr_number == 100
    assert "superseded" in comment_body
    assert "PR #1234" in comment_body


def test_close_pr_changes_state() -> None:
    """Test that the PR state changes to closed."""
    issue = _make_issue(55, "Open Issue", "Body")
    fake_gh = FakeGitHubIssues(issues={55: issue})
    fake_github = FakeGitHub(
        pr_details={55: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    result = runner.invoke(
        close_pr,
        ["55", "--comment", "Done"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    assert result.exit_code == 0

    # Verify the PR state was updated in the fake
    closed_pr = fake_github.get_pr(None, 55)
    assert not isinstance(closed_pr, PRNotFound)
    assert closed_pr.state == "CLOSED"


def test_close_pr_requires_comment_flag() -> None:
    """Test that --comment flag is required."""
    issue = _make_issue(10, "Test", "Body")
    fake_gh = FakeGitHubIssues(issues={10: issue})
    fake_github = FakeGitHub(
        pr_details={10: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    result = runner.invoke(
        close_pr,
        ["10"],  # Missing --comment
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
        ),
    )

    # Click should reject missing required option
    assert result.exit_code == 2
    assert "comment" in result.output.lower()
