"""Unit tests for objective-roadmap-update command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_roadmap_update import (
    objective_roadmap_update,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

SAMPLE_BODY = """# Objective: Test Feature

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Setup infrastructure | - | #100 |
| 1.2 | Add basic tests | - | plan #101 |
| 1.3 | Update docs | - | - |

### Phase 2: Core Implementation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Build main feature | - | - |
| 2.2 | Add integration tests | blocked | - |
| 2.3 | Performance tuning | skipped | - |
"""


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
        labels=["erk-objective"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_update_pr_column_only() -> None:
    """Test updating only the PR column on a pending step."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "2.1", "--pr", "#200"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["issue_number"] == 100
    assert output["step"]["id"] == "2.1"
    assert output["step"]["pr"] == "#200"
    # PR #200 means status inferred as "done"
    assert output["step"]["status"] == "done"

    # Verify the body was updated via the fake
    assert len(fake_gh.updated_bodies) == 1
    updated_number, updated_body = fake_gh.updated_bodies[0]
    assert updated_number == 100
    assert "#200" in updated_body


def test_update_status_column_only() -> None:
    """Test updating only the status column on a pending step."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "2.1", "--status", "blocked"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["step"]["id"] == "2.1"
    assert output["step"]["status"] == "blocked"


def test_update_both_columns() -> None:
    """Test updating both status and PR columns."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "1.3", "--status", "done", "--pr", "#150"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["step"]["id"] == "1.3"
    assert output["step"]["pr"] == "#150"
    # Status column "done" is not a recognized override (only blocked/skipped),
    # so PR inference kicks in: #150 -> done
    assert output["step"]["status"] == "done"


def test_step_not_found() -> None:
    """Test error when step ID does not exist in the roadmap."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "9.9", "--status", "done"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "9.9" in output["error"]
    assert "not found" in output["error"]


def test_issue_not_found() -> None:
    """Test error when objective issue does not exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["999", "--step", "1.1", "--status", "done"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]


def test_no_flags_provided() -> None:
    """Test error when neither --status nor --pr is provided."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "1.1"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "at least one" in output["error"].lower()


def test_revalidation_after_mutation() -> None:
    """Test that the post-mutation check returns valid summary data."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "1.3", "--pr", "#160"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Summary should reflect the updated state
    summary = output["summary"]
    assert summary["total_steps"] == 6
    # 1.1 done (#100), 1.2 in_progress (plan #101), 1.3 now done (#160),
    # 2.1 pending, 2.2 blocked, 2.3 skipped
    assert summary["done"] == 2
    assert summary["in_progress"] == 1
    assert summary["pending"] == 1
    assert summary["blocked"] == 1
    assert summary["skipped"] == 1

    assert output["validation_errors"] == []


def test_plan_pr_reference() -> None:
    """Test that setting --pr to 'plan #456' results in in_progress status."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "2.1", "--pr", "plan #456"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["step"]["id"] == "2.1"
    assert output["step"]["pr"] == "plan #456"
    assert output["step"]["status"] == "in_progress"


def test_preserves_other_rows() -> None:
    """Test that updating one row does not modify other rows."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "1.3", "--pr", "#170"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0

    # Verify the updated body still has the other rows intact
    _, updated_body = fake_gh.updated_bodies[0]
    assert "| 1.1 | Setup infrastructure | - | #100 |" in updated_body
    assert "| 1.2 | Add basic tests | - | plan #101 |" in updated_body
    assert "| 2.1 | Build main feature | - | - |" in updated_body
    assert "| 2.2 | Add integration tests | blocked | - |" in updated_body
    assert "| 2.3 | Performance tuning | skipped | - |" in updated_body
    # The updated row should have the new PR
    assert "| 1.3 | Update docs | - | #170 |" in updated_body


def test_pr_clears_blocked_status() -> None:
    """Test that setting --pr on a blocked step resets the status cell for inference.

    This is the key inference-driven behavior: when --pr is provided without
    --status, the Status cell resets to "-" so the parser infers from the PR column.
    A blocked step with PR #250 should become "done", not stay "blocked".
    """
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    # Step 2.2 is "blocked" — setting PR should clear the blocked override
    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "2.2", "--pr", "#250"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["step"]["id"] == "2.2"
    assert output["step"]["pr"] == "#250"
    # Inference: #250 -> done (blocked override was cleared)
    assert output["step"]["status"] == "done"

    # Verify the markdown cell was reset to "-" for status
    _, updated_body = fake_gh.updated_bodies[0]
    assert "| 2.2 | Add integration tests | - | #250 |" in updated_body


def test_update_step_in_second_phase() -> None:
    """Test that updating a step in Phase 2 works correctly."""
    issue = _make_issue(100, "Objective: Test Feature", SAMPLE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_update,
        ["100", "--step", "2.2", "--status", "-", "--pr", "#250"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["step"]["id"] == "2.2"
    assert output["step"]["pr"] == "#250"
    # Status column is "-" which is not blocked/skipped, and PR is #250 -> done
    assert output["step"]["status"] == "done"
