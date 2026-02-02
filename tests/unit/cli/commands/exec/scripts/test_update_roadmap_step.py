"""Unit tests for update-roadmap-step command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_roadmap_step import update_roadmap_step
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

ROADMAP_BODY = """\
# Objective: Build Feature X

## Roadmap

### Phase 1: Foundation (1 PR)

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Set up project structure | - | #100 |
| 1.2 | Add core types | - | plan #200 |
| 1.3 | Add utility functions | - | - |

### Phase 2: Implementation (1 PR)

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Implement main feature | - | - |
| 2.2 | Add tests | blocked | - |
"""

NO_ROADMAP_BODY = """\
# Objective: Simple Issue

No roadmap table here, just some text.
"""


def _make_issue(number: int, body: str) -> IssueInfo:
    """Create a test IssueInfo with a roadmap body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Objective #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_update_pending_step_with_plan_pr() -> None:
    """Update a pending step with a plan PR reference."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "plan #6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6423
    assert output["step_id"] == "1.3"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "plan #6464"
    assert output["url"] == "https://github.com/test/repo/issues/6423"

    # Verify the body was updated
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "plan #6464" in updated_body
    # Status cell should be "in-progress" for plan PR
    assert "| 1.3 " in updated_body
    assert "| in-progress |" in updated_body


def test_update_step_with_existing_pr() -> None:
    """Update a step that already has a PR reference."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.2", "--pr", "#500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["previous_pr"] == "plan #200"
    assert output["new_pr"] == "#500"

    # Verify the body was updated
    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    # The old "plan #200" should be replaced
    assert "plan #200" not in updated_body
    # Status cell should be "done" for merged PR
    assert "| done |" in updated_body


def test_clear_pr_reference() -> None:
    """Clear a step's PR reference by passing empty string."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.1", "--pr", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["previous_pr"] == "#100"
    assert output["new_pr"] is None

    # Verify the body was updated with "-" in PR cell
    updated_body = fake_gh.updated_bodies[0][1]
    # The row for 1.1 should now have "-" in PR cell
    assert "#100" not in updated_body
    # Status cell should be "pending" when PR is cleared
    assert "| pending |" in updated_body


def test_step_not_found() -> None:
    """Error when step ID doesn't exist in roadmap."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "9.9", "--pr", "plan #123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "step_not_found"
    assert "9.9" in output["message"]


def test_issue_not_found() -> None:
    """Error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["999", "--step", "1.1", "--pr", "#123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "999" in output["message"]


def test_no_roadmap_table() -> None:
    """Error when issue has no roadmap table."""
    issue = _make_issue(6423, NO_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.1", "--pr", "#123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


def test_update_step_in_phase_2() -> None:
    """Update a step in a later phase."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "2.1", "--pr", "plan #300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["step_id"] == "2.1"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "plan #300"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "plan #300" in updated_body
