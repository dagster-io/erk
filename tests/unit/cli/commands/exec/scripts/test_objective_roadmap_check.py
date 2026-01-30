"""Unit tests for objective-roadmap-check command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_roadmap_check import (
    objective_roadmap_check,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


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


def test_well_formed_objective() -> None:
    """Test parsing a well-formed objective with multiple phases and mixed statuses."""
    body = """# Objective: Test Feature

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Setup infrastructure | - | #123 |
| 1.2 | Add basic tests | - | plan #124 |
| 1.3 | Update docs | - | - |

### Phase 2: Core Implementation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Build main feature | - | #125 |
| 2.2 | Add integration tests | blocked | - |
| 2.3 | Performance tuning | skipped | - |
"""
    issue = _make_issue(100, "Objective: Test Feature", body)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["100"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["issue_number"] == 100
    assert output["title"] == "Objective: Test Feature"

    # Verify phases structure
    assert len(output["phases"]) == 2

    phase1 = output["phases"][0]
    assert phase1["number"] == 1
    assert phase1["name"] == "Foundation"
    assert len(phase1["steps"]) == 3

    # Check status inference
    assert phase1["steps"][0]["status"] == "done"  # Has #123
    assert phase1["steps"][1]["status"] == "in_progress"  # Has plan #124
    assert phase1["steps"][2]["status"] == "pending"  # Empty

    phase2 = output["phases"][1]
    assert phase2["number"] == 2
    assert phase2["name"] == "Core Implementation"
    assert len(phase2["steps"]) == 3

    assert phase2["steps"][0]["status"] == "done"  # Has #125
    assert phase2["steps"][1]["status"] == "blocked"  # Status column overrides
    assert phase2["steps"][2]["status"] == "skipped"  # Status column overrides

    # Verify summary
    summary = output["summary"]
    assert summary["total_steps"] == 6
    assert summary["done"] == 2
    assert summary["in_progress"] == 1
    assert summary["pending"] == 1
    assert summary["blocked"] == 1
    assert summary["skipped"] == 1

    # Verify next step is the first pending
    next_step = output["next_step"]
    assert next_step is not None
    assert next_step["id"] == "1.3"
    assert next_step["description"] == "Update docs"
    assert next_step["phase"] == "Foundation"

    assert output["validation_errors"] == []


def test_all_pending() -> None:
    """Test objective where all steps are pending."""
    body = """# Objective: New Feature

## Roadmap

### Phase 1: Start

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | First task | - | - |
| 1.2 | Second task | - | - |
"""
    issue = _make_issue(200, "Objective: New Feature", body)
    fake_gh = FakeGitHubIssues(issues={200: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["200"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["summary"]["total_steps"] == 2
    assert output["summary"]["pending"] == 2
    assert output["summary"]["done"] == 0

    # Next step should be the first one
    assert output["next_step"]["id"] == "1.1"


def test_all_done() -> None:
    """Test objective where all steps are complete."""
    body = """# Objective: Completed Feature

## Roadmap

### Phase 1: Done

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | First task | - | #100 |
| 1.2 | Second task | - | #101 |
"""
    issue = _make_issue(300, "Objective: Completed Feature", body)
    fake_gh = FakeGitHubIssues(issues={300: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["summary"]["done"] == 2
    assert output["summary"]["pending"] == 0

    # No next step when all done
    assert output["next_step"] is None


def test_mixed_statuses() -> None:
    """Test status inference with all status types."""
    body = """# Objective: Mixed Status Test

## Roadmap

### Phase 1: Test All States

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Pending task | - | - |
| 1.2 | Done task | - | #42 |
| 1.3 | In progress task | - | plan #43 |
| 1.4 | Blocked task | blocked | - |
| 1.5 | Skipped task | skipped | #99 |
"""
    issue = _make_issue(400, "Objective: Mixed Status Test", body)
    fake_gh = FakeGitHubIssues(issues={400: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["400"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    steps = output["phases"][0]["steps"]
    assert steps[0]["status"] == "pending"
    assert steps[1]["status"] == "done"
    assert steps[2]["status"] == "in_progress"
    assert steps[3]["status"] == "blocked"
    assert steps[4]["status"] == "skipped"  # Status column wins over PR


def test_letter_format_step_ids() -> None:
    """Test that letter-format step IDs are accepted with a warning."""
    body = """# Objective: Letter Format Test

## Roadmap

### Phase 1A: Test Phase

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1A.1 | Task with letter | - | - |
| 1A.2 | Another task | - | #100 |
"""
    issue = _make_issue(500, "Objective: Letter Format Test", body)
    fake_gh = FakeGitHubIssues(issues={500: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert len(output["phases"]) == 1

    # Should have warnings about letter format
    assert len(output["validation_errors"]) >= 2
    assert any("1A.1" in err and "letter format" in err for err in output["validation_errors"])
    assert any("1A.2" in err and "letter format" in err for err in output["validation_errors"])


def test_no_roadmap_tables() -> None:
    """Test error when objective has no roadmap tables."""
    body = """# Objective: No Roadmap

This objective has no roadmap tables.

Just some text content.
"""
    issue = _make_issue(600, "Objective: No Roadmap", body)
    fake_gh = FakeGitHubIssues(issues={600: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["600"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)

    assert output["success"] is False
    assert "validation_errors" in output
    assert any("No phase headers found" in err for err in output["validation_errors"])


def test_status_column_overrides_pr_column() -> None:
    """Test that status column (blocked/skipped) overrides PR column."""
    body = """# Objective: Status Override Test

## Roadmap

### Phase 1: Test Overrides

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Blocked with PR | blocked | #100 |
| 1.2 | Skipped with plan | skipped | plan #101 |
"""
    issue = _make_issue(700, "Objective: Status Override Test", body)
    fake_gh = FakeGitHubIssues(issues={700: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["700"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    steps = output["phases"][0]["steps"]
    assert steps[0]["status"] == "blocked"  # Not "done" despite PR
    assert steps[0]["pr"] == "#100"  # PR value is preserved
    assert steps[1]["status"] == "skipped"  # Not "in_progress" despite plan PR
    assert steps[1]["pr"] == "plan #101"


def test_issue_not_found() -> None:
    """Test error when objective issue does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty issues dict
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]


def test_phase_with_pr_count_in_header() -> None:
    """Test that phase headers with PR counts are parsed correctly."""
    body = """# Objective: PR Count Test

## Roadmap

### Phase 1: Foundation (3 PR)

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | First task | - | #100 |
| 1.2 | Second task | - | #101 |
| 1.3 | Third task | - | #102 |
"""
    issue = _make_issue(800, "Objective: PR Count Test", body)
    fake_gh = FakeGitHubIssues(issues={800: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["800"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Phase name should not include the PR count
    assert output["phases"][0]["name"] == "Foundation"
    assert len(output["phases"][0]["steps"]) == 3


def test_empty_pr_column_with_dash() -> None:
    """Test that dashes in PR column are treated as empty."""
    body = """# Objective: Dash Test

## Roadmap

### Phase 1: Test Dashes

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Task with dash | - | - |
| 1.2 | Task without dash | - | |
"""
    issue = _make_issue(900, "Objective: Dash Test", body)
    fake_gh = FakeGitHubIssues(issues={900: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["900"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    steps = output["phases"][0]["steps"]
    # Both should be pending with no PR
    assert steps[0]["status"] == "pending"
    assert steps[0]["pr"] is None
    assert steps[1]["status"] == "pending"
    assert steps[1]["pr"] is None
