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


def test_malformed_table_missing_separator() -> None:
    """Test that a table header without separator line produces a validation error."""
    body = """# Objective: Missing Separator

## Roadmap

### Phase 1: Has Separator

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Good row | - | - |

### Phase 2: No Separator

| Step | Description | Status | PR |
| 2.1 | Bad row | - | - |
"""
    issue = _make_issue(1000, "Objective: Missing Separator", body)
    fake_gh = FakeGitHubIssues(issues={1000: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1000"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Phase 1 should parse fine, phase 2 should have a validation error
    assert output["success"] is True
    assert len(output["phases"]) == 1
    assert output["phases"][0]["number"] == 1
    assert any(
        "Phase 2" in err and "missing separator" in err for err in output["validation_errors"]
    )


def test_malformed_table_wrong_column_count() -> None:
    """Test that rows with wrong column count are silently skipped."""
    body = """# Objective: Wrong Columns

## Roadmap

### Phase 1: Bad Rows

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Only three cols | - |
| 1.2 | Also three cols | - |
"""
    issue = _make_issue(1100, "Objective: Wrong Columns", body)
    fake_gh = FakeGitHubIssues(issues={1100: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1100"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # All rows malformed → no steps → validation error → no phases → exit 1
    assert result.exit_code == 1
    output = json.loads(result.output)

    assert output["success"] is False
    assert any("Phase 1 has no table rows" in err for err in output["validation_errors"])


def test_phase_header_without_table() -> None:
    """Test that a phase header followed by prose (no table) produces validation error."""
    body = """# Objective: No Table

## Roadmap

### Phase 1: Has Table

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Good step | - | #50 |

### Phase 2: Prose Only

This phase has no table, just text explaining things.
Some more prose here.
"""
    issue = _make_issue(1200, "Objective: No Table", body)
    fake_gh = FakeGitHubIssues(issues={1200: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1200"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert len(output["phases"]) == 1
    assert output["phases"][0]["number"] == 1
    assert any(
        "Phase 2" in err and "missing roadmap table" in err for err in output["validation_errors"]
    )


def test_empty_table_no_data_rows() -> None:
    """Test that a table with header and separator but no data rows is flagged."""
    body = """# Objective: Empty Table

## Roadmap

### Phase 1: Empty

| Step | Description | Status | PR |
|------|-------------|--------|-----|
"""
    issue = _make_issue(1300, "Objective: Empty Table", body)
    fake_gh = FakeGitHubIssues(issues={1300: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # No rows → no phases → exit 1
    assert result.exit_code == 1
    output = json.loads(result.output)

    assert output["success"] is False
    assert any("Phase 1 has no table rows" in err for err in output["validation_errors"])


def test_mixed_step_id_formats() -> None:
    """Test that plain numeric IDs produce no warnings but letter-format IDs do."""
    body = """# Objective: Mixed IDs

## Roadmap

### Phase 1: Plain Numbers

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Plain number | - | - |
| 1.2 | Also plain | - | - |

### Phase 2A: Letter Format

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2A.1 | Letter id | - | - |
| 2A.2 | Also letter | - | - |
"""
    issue = _make_issue(1400, "Objective: Mixed IDs", body)
    fake_gh = FakeGitHubIssues(issues={1400: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1400"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert len(output["phases"]) == 2

    # Only letter-format IDs should produce warnings
    letter_warnings = [err for err in output["validation_errors"] if "letter format" in err]
    assert len(letter_warnings) == 2
    assert any("2A.1" in w for w in letter_warnings)
    assert any("2A.2" in w for w in letter_warnings)

    # No warnings for plain numbers
    assert not any("1.1" in err for err in output["validation_errors"])
    assert not any("1.2" in err for err in output["validation_errors"])


def test_real_world_body_structure() -> None:
    """Test parsing with surrounding non-roadmap content (design decisions, focus sections)."""
    body = """# Objective: Real World Feature

## Design Decisions

- Decision 1: Use approach A
- Decision 2: Prefer pattern B

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Setup | - | #10 |
| 1.2 | Config | - | plan #11 |

**Test:** Verify setup works end-to-end

### Phase 2: Implementation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Core logic | - | - |

## Current Focus

Working on Phase 1 currently.

## Notes

Some additional notes here.
"""
    issue = _make_issue(1500, "Objective: Real World Feature", body)
    fake_gh = FakeGitHubIssues(issues={1500: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert len(output["phases"]) == 2

    # Verify only roadmap table content is extracted
    assert output["phases"][0]["steps"][0]["status"] == "done"
    assert output["phases"][0]["steps"][1]["status"] == "in_progress"
    assert output["phases"][1]["steps"][0]["status"] == "pending"

    assert output["summary"]["total_steps"] == 3
    assert output["validation_errors"] == []


def test_done_in_status_column() -> None:
    """Test that 'done' text in status column does not override PR-based inference.

    The code only checks for 'blocked' and 'skipped' in the status column.
    'done' in the status column with no PR results in 'pending' status.
    """
    body = """# Objective: Done Status Test

## Roadmap

### Phase 1: Status Done

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Explicit done no PR | done | - |
| 1.2 | Explicit done with PR | done | #100 |
"""
    issue = _make_issue(1600, "Objective: Done Status Test", body)
    fake_gh = FakeGitHubIssues(issues={1600: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1600"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    steps = output["phases"][0]["steps"]
    # 'done' in status column is NOT handled — falls through to PR-based inference
    # No PR → pending
    assert steps[0]["status"] == "pending"
    # Has PR #100 → done (from PR inference, not status column)
    assert steps[1]["status"] == "done"


def test_non_sequential_phase_numbers() -> None:
    """Test that phases with gaps in numbering are all parsed correctly."""
    body = """# Objective: Gaps Test

## Roadmap

### Phase 1: First

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Step one | - | #1 |

### Phase 3: Third

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 3.1 | Step three | - | - |

### Phase 5: Fifth

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 5.1 | Step five | - | plan #5 |
"""
    issue = _make_issue(1700, "Objective: Gaps Test", body)
    fake_gh = FakeGitHubIssues(issues={1700: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1700"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert len(output["phases"]) == 3
    assert output["phases"][0]["number"] == 1
    assert output["phases"][1]["number"] == 3
    assert output["phases"][2]["number"] == 5

    assert output["summary"]["total_steps"] == 3
    assert output["validation_errors"] == []


def test_pr_column_variations() -> None:
    """Test various PR column formats and their status inference."""
    body = """# Objective: PR Variations

## Roadmap

### Phase 1: PR Formats

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Hash PR | - | #123 |
| 1.2 | Plan lowercase | - | plan #123 |
| 1.3 | Plan capitalized | - | Plan #123 |
| 1.4 | Multiple PRs | - | #123, #124 |
"""
    issue = _make_issue(1800, "Objective: PR Variations", body)
    fake_gh = FakeGitHubIssues(issues={1800: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1800"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    steps = output["phases"][0]["steps"]
    # #123 → done
    assert steps[0]["status"] == "done"
    assert steps[0]["pr"] == "#123"
    # plan #123 → in_progress
    assert steps[1]["status"] == "in_progress"
    assert steps[1]["pr"] == "plan #123"
    # Plan #123 (capitalized) → pending (case-sensitive startswith("plan #"))
    assert steps[2]["status"] == "pending"
    assert steps[2]["pr"] == "Plan #123"
    # #123, #124 → done (starts with #)
    assert steps[3]["status"] == "done"
    assert steps[3]["pr"] == "#123, #124"


def test_single_phase_single_step() -> None:
    """Test minimal valid objective: one phase, one step."""
    body = """# Objective: Minimal

## Roadmap

### Phase 1: Only Phase

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Only step | - | - |
"""
    issue = _make_issue(1900, "Objective: Minimal", body)
    fake_gh = FakeGitHubIssues(issues={1900: issue})
    runner = CliRunner()

    result = runner.invoke(
        objective_roadmap_check,
        ["1900"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert output["success"] is True
    assert len(output["phases"]) == 1
    assert len(output["phases"][0]["steps"]) == 1
    assert output["phases"][0]["steps"][0]["id"] == "1.1"
    assert output["phases"][0]["steps"][0]["status"] == "pending"
    assert output["summary"]["total_steps"] == 1
    assert output["summary"]["pending"] == 1
    assert output["next_step"]["id"] == "1.1"
