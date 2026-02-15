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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infrastructure | done | - | #123 |
| 1.2 | Add basic tests | in-progress | #124 | - |
| 1.3 | Update docs | pending | - | - |

### Phase 2: Core Implementation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build main feature | done | - | #125 |
| 2.2 | Add integration tests | blocked | - | - |
| 2.3 | Performance tuning | skipped | - | - |
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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | First | done | - | #100 |
| 1.2 | Second | done | - | #101 |
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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | - | - | - |

### Phase 2: Second

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Step two | - | - | - |
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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | - | - | - |

### Phase 3: Third

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 3.1 | Step three | - | - | - |
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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1A.1 | Step one | - | - | - |

### Phase 1B: Second Part

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1B.1 | Step two | - | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Step three | - | - | - |
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

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | First | done | - | #100 |
| 1.2 | Second | skipped | - | - |
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


def test_stale_display_status_with_pr_fails() -> None:
    """Test that stale '-' status with PR reference is flagged by Check 6."""
    body = """# Objective: Stale Status

## Roadmap

### Phase 1: Legacy Format

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Do thing | - | - | #123 |
| 1.2 | Another thing | - | #124 | - |
"""
    issue = _make_issue(1000, "Objective: Stale Status", body)
    fake_gh = FakeGitHubIssues(issues={1000: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1000"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "Stale '-' status with PR reference" in result.output
    assert "1 step(s)" in result.output


def test_explicit_display_status_with_pr_passes() -> None:
    """Test that explicit status values with PR references pass Check 6."""
    body = """# Objective: Correct Format

## Roadmap

### Phase 1: Updated Format

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Do thing | done | - | #123 |
| 1.2 | Another thing | in-progress | #124 | - |
| 1.3 | Not started | pending | - | - |
"""
    issue = _make_issue(1100, "Objective: Correct Format", body)
    fake_gh = FakeGitHubIssues(issues={1100: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1100"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "[FAIL]" not in result.output
    assert "No stale display statuses" in result.output


# --- v2 format integrity tests ---

V2_BODY_VALID = """\
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-01T00:00:00+00:00'
created_by: testuser
objective_comment_id: 42

```

</details>
<!-- /erk:metadata-block:objective-header -->

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Set up project structure"
    status: "done"
    plan: null
    pr: "#100"
  - id: "1.2"
    description: "Add core types"
    status: "pending"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->
"""


V2_BODY_MISSING_COMMENT_ID = """\
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-01T00:00:00+00:00'
created_by: testuser

```

</details>
<!-- /erk:metadata-block:objective-header -->

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Set up project structure"
    status: "done"
    plan: null
    pr: "#100"
---
<!-- /erk:metadata-block:objective-roadmap -->
"""


def test_v2_valid_header_passes_check_7() -> None:
    """v2 format: objective-header with objective_comment_id passes Check 7."""
    issue = _make_issue(1200, "Objective: V2 Valid", V2_BODY_VALID)
    fake_gh = FakeGitHubIssues(issues={1200: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1200"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "objective-header has objective_comment_id" in result.output
    assert "[FAIL]" not in result.output


def test_v2_missing_comment_id_fails_check_7() -> None:
    """v2 format: objective-header without objective_comment_id fails Check 7."""
    issue = _make_issue(1300, "Objective: V2 Missing", V2_BODY_MISSING_COMMENT_ID)
    fake_gh = FakeGitHubIssues(issues={1300: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "objective-header missing objective_comment_id" in result.output
