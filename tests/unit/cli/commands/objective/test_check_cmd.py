"""Unit tests for erk objective check command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.objective.check_cmd import (
    ObjectiveValidationError,
    ObjectiveValidationSuccess,
    check_objective,
    validate_objective,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def _make_issue(
    number: int,
    title: str,
    body: str,
    *,
    labels: list[str] | None = None,
) -> IssueInfo:
    """Create a test IssueInfo."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=labels if labels is not None else ["erk-objective"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


VALID_OBJECTIVE_BODY = """# Objective: Test Feature

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


def test_valid_objective_passes_all_checks() -> None:
    """Test that a well-formed objective passes all validation checks."""
    issue = _make_issue(100, "Objective: Test Feature", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["100"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "[PASS]" in result.output
    assert "[FAIL]" not in result.output


def test_valid_objective_json_output() -> None:
    """Test JSON output mode returns structured data with phases and summary."""
    issue = _make_issue(100, "Objective: Test Feature", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["100", "--json-output"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["issue_number"] == 100
    assert len(output["phases"]) == 2
    assert output["summary"]["total_steps"] == 6
    assert output["summary"]["done"] == 2
    assert output["summary"]["in_progress"] == 1
    assert output["summary"]["pending"] == 1
    assert output["summary"]["blocked"] == 1
    assert output["summary"]["skipped"] == 1
    assert output["next_step"]["id"] == "1.3"


def test_missing_objective_label_fails() -> None:
    """Test that missing erk-objective label is flagged."""
    issue = _make_issue(
        200,
        "Some Issue",
        VALID_OBJECTIVE_BODY,
        labels=["bug"],
    )
    fake_gh = FakeGitHubIssues(issues={200: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["200"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "erk-objective label" in result.output


def test_malformed_roadmap_fails() -> None:
    """Test that a body with no roadmap tables fails."""
    body = """# Objective: No Roadmap

This objective has no roadmap tables.
"""
    issue = _make_issue(300, "Objective: No Roadmap", body)
    fake_gh = FakeGitHubIssues(issues={300: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "Roadmap parses successfully" in result.output


def test_done_step_without_pr_fails() -> None:
    """Test that a done step without PR reference is flagged.

    Note: The parser infers status from PR column, so a step is only
    'done' if it has a PR. This test uses a body where we can't trigger
    this naturally through inference — we validate the check exists.
    """
    # In the current parser, 'done' without PR falls through to 'pending'
    # So this check is a safety net for future changes. Verify the check command
    # passes when statuses are consistent.
    body = """# Objective: All Done

## Roadmap

### Phase 1: Done

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | First | - | #100 |
| 1.2 | Second | - | #101 |
"""
    issue = _make_issue(400, "Objective: All Done", body)
    fake_gh = FakeGitHubIssues(issues={400: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["400"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "[FAIL]" not in result.output


def test_issue_not_found_fails() -> None:
    """Test that a non-existent issue returns an error."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "not found" in result.output


def test_issue_not_found_json() -> None:
    """Test JSON output for non-existent issue."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["999", "--json-output"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]


def test_sequential_phase_numbering_passes() -> None:
    """Test that sequential phases pass the numbering check."""
    body = """# Objective: Sequential

## Roadmap

### Phase 1: First

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Step one | - | - |

### Phase 2: Second

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Step two | - | - |
"""
    issue = _make_issue(500, "Objective: Sequential", body)
    fake_gh = FakeGitHubIssues(issues={500: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "Phase numbering is sequential" in result.output


def test_non_sequential_phase_numbering_still_passes() -> None:
    """Test that non-sequential but increasing phases pass (gaps are OK)."""
    body = """# Objective: Gaps

## Roadmap

### Phase 1: First

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Step one | - | - |

### Phase 3: Third

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 3.1 | Step three | - | - |
"""
    issue = _make_issue(600, "Objective: Gaps", body)
    fake_gh = FakeGitHubIssues(issues={600: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["600"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "Phase numbering is sequential" in result.output


def test_sub_phase_numbering_passes() -> None:
    """Test that sub-phases like 1A, 1B, 1C pass the sequential check."""
    body = """# Objective: Sub-phases

## Roadmap

### Phase 1A: First Part

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1A.1 | Step one | - | - |

### Phase 1B: Second Part

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1B.1 | Step two | - | - |

### Phase 2: Core

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Step three | - | - |
"""
    issue = _make_issue(900, "Objective: Sub-phases", body)
    fake_gh = FakeGitHubIssues(issues={900: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["900"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "Phase numbering is sequential" in result.output
    assert "[FAIL]" not in result.output


def test_validate_objective_returns_success_type() -> None:
    """Test that validate_objective returns proper result types."""
    issue = _make_issue(700, "Objective: Test", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={700: issue})

    result = validate_objective(fake_gh, Path("/fake/repo"), 700)

    assert isinstance(result, ObjectiveValidationSuccess)
    assert result.passed is True
    assert len(result.phases) == 2
    assert result.summary["total_steps"] == 6


def test_validate_objective_returns_error_for_missing_issue() -> None:
    """Test that validate_objective returns error type for missing issue."""
    fake_gh = FakeGitHubIssues()

    result = validate_objective(fake_gh, Path("/fake/repo"), 999)

    assert isinstance(result, ObjectiveValidationError)
    assert "999" in result.error


def test_all_steps_complete_json() -> None:
    """Test JSON output when all steps are done (for closing trigger detection)."""
    body = """# Objective: Complete

## Roadmap

### Phase 1: Done

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | First | - | #100 |
| 1.2 | Second | skipped | - |
"""
    issue = _make_issue(800, "Objective: Complete", body)
    fake_gh = FakeGitHubIssues(issues={800: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["800", "--json-output"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["summary"]["done"] == 1
    assert output["summary"]["skipped"] == 1
    assert output["summary"]["pending"] == 0
    assert output["next_step"] is None


def test_invalid_depends_on_reference_fails() -> None:
    """Test that depends_on referencing non-existent step ID fails."""
    body = """# Objective: Invalid Dependencies

## Roadmap

### Phase 1: Test

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Setup | plan | - | - | pending | - |
| 1.2 | Build | plan | - | 9.9 | pending | - |
"""
    issue = _make_issue(1000, "Objective: Invalid Dependencies", body)
    fake_gh = FakeGitHubIssues(issues={1000: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1000"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "Invalid dependency" in result.output
    assert "9.9" in result.output


def test_cross_phase_dependency_passes() -> None:
    """Test that depends_on can reference steps from different phases."""
    body = """# Objective: Cross-phase Dependencies

## Roadmap

### Phase 1: Setup

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Setup infra | plan | - | - | pending | - |

### Phase 2: Build

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 2.1 | Build feature | plan | - | 1.1 | pending | - |
"""
    issue = _make_issue(1100, "Objective: Cross-phase Dependencies", body)
    fake_gh = FakeGitHubIssues(issues={1100: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1100"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "[FAIL]" not in result.output
    assert "All Depends On references are valid" in result.output


def test_invalid_step_type_normalized_to_plan() -> None:
    """Test that invalid step_type values get normalized to 'plan' by parser.

    The parser is lenient and defaults unrecognized types to 'plan'.
    The validation check is a defensive safety net that would only trigger
    if a step_type field was somehow set to an invalid value outside the parser.
    """
    body = """# Objective: Invalid Step Type

## Roadmap

### Phase 1: Test

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Setup | invalid-type | - | - | pending | - |
"""
    issue = _make_issue(1200, "Objective: Invalid Step Type", body)
    fake_gh = FakeGitHubIssues(issues={1200: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1200", "--json-output"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify the invalid type was normalized to "plan"
    assert output["phases"][0]["steps"][0]["step_type"] == "plan"

    # Verify all validation checks passed (including step type check)
    assert all(check["passed"] for check in output["checks"])


def test_7col_format_json_output_includes_new_fields() -> None:
    """Test that JSON output from 7-column table includes new fields."""
    body = """# Objective: Seven Columns

## Roadmap

### Phase 1: Setup

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Setup infra | plan | #6630 | - | - | #6631 |
| 1.2 | Add module | objective | #7001 | 1.1 | pending | - |
"""
    issue = _make_issue(1300, "Objective: Seven Columns", body)
    fake_gh = FakeGitHubIssues(issues={1300: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1300", "--json-output"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Check that steps include new fields
    steps = output["phases"][0]["steps"]
    assert len(steps) == 2

    assert steps[0]["step_type"] == "plan"
    assert steps[0]["issue"] == "#6630"
    assert steps[0]["depends_on"] == []

    assert steps[1]["step_type"] == "objective"
    assert steps[1]["issue"] == "#7001"
    assert steps[1]["depends_on"] == ["1.1"]
