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


def test_update_multiple_steps_success() -> None:
    """Update multiple steps in a single operation - all succeed."""
    issue = _make_issue(6697, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.2", "--step", "1.3", "--step", "2.1", "--pr", "plan #6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6697
    assert output["new_pr"] == "plan #6759"
    assert output["url"] == "https://github.com/test/repo/issues/6697"

    # Verify steps array
    assert "steps" in output
    assert len(output["steps"]) == 3

    # Check step 1.2 (previously had "plan #200")
    step_1_2 = next(s for s in output["steps"] if s["step_id"] == "1.2")
    assert step_1_2["success"] is True
    assert step_1_2["previous_pr"] == "plan #200"

    # Check step 1.3 (previously empty)
    step_1_3 = next(s for s in output["steps"] if s["step_id"] == "1.3")
    assert step_1_3["success"] is True
    assert step_1_3["previous_pr"] is None

    # Check step 2.1 (previously empty)
    step_2_1 = next(s for s in output["steps"] if s["step_id"] == "2.1")
    assert step_2_1["success"] is True
    assert step_2_1["previous_pr"] is None

    # Verify single API call was made
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]

    # All three steps should have the new PR
    assert updated_body.count("plan #6759") == 3
    # Old PR should be gone
    assert "plan #200" not in updated_body


def test_update_multiple_steps_partial_failure() -> None:
    """Multi-step update rejected upfront when any step is missing."""
    issue = _make_issue(6697, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.2", "--step", "9.9", "--step", "2.1", "--pr", "plan #6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Multi-step exits 0 even on failure (check JSON success field)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["issue_number"] == 6697
    assert output["new_pr"] == "plan #6759"

    # Only the missing step appears in results (upfront validation)
    assert len(output["steps"]) == 1
    assert output["steps"][0]["step_id"] == "9.9"
    assert output["steps"][0]["success"] is False
    assert output["steps"][0]["error"] == "step_not_found"

    # No API call should have been made (upfront rejection)
    assert len(fake_gh.updated_bodies) == 0


def test_update_multiple_steps_same_phase() -> None:
    """Update multiple steps within the same phase."""
    issue = _make_issue(6697, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.1", "--step", "1.2", "--step", "1.3", "--pr", "#555"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # All three steps in Phase 1 should be updated
    assert len(output["steps"]) == 3
    for step_result in output["steps"]:
        assert step_result["success"] is True

    # Verify all steps have merged PR status
    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("#555") == 3
    # All should have "done" status
    assert updated_body.count("| done |") >= 3


def test_update_multiple_steps_cross_phase() -> None:
    """Update steps across different phases."""
    issue = _make_issue(6697, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.1", "--step", "2.2", "--pr", "plan #777"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["steps"]) == 2

    # Both steps should succeed
    step_1_1 = next(s for s in output["steps"] if s["step_id"] == "1.1")
    assert step_1_1["success"] is True
    assert step_1_1["previous_pr"] == "#100"

    step_2_2 = next(s for s in output["steps"] if s["step_id"] == "2.2")
    assert step_2_2["success"] is True
    assert step_2_2["previous_pr"] is None

    # Verify both phases updated
    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("plan #777") == 2


def test_single_step_maintains_legacy_format() -> None:
    """Single --step usage maintains backward-compatible output format."""
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

    # Should use legacy format (no "steps" array)
    assert "steps" not in output
    assert output["success"] is True
    assert output["step_id"] == "1.3"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "plan #6464"


def test_update_multiple_steps_all_fail() -> None:
    """Multi-step update where ALL steps fail (none found in roadmap)."""
    issue = _make_issue(6697, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "9.1", "--step", "9.2", "--step", "9.3", "--pr", "plan #6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Multi-step exits 0 even on failure (check JSON success field)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["issue_number"] == 6697
    assert output["new_pr"] == "plan #6759"

    # All three missing steps in results
    assert len(output["steps"]) == 3
    for step_result in output["steps"]:
        assert step_result["success"] is False
        assert step_result["error"] == "step_not_found"

    step_ids = [s["step_id"] for s in output["steps"]]
    assert step_ids == ["9.1", "9.2", "9.3"]

    # No API call should have been made
    assert len(fake_gh.updated_bodies) == 0
