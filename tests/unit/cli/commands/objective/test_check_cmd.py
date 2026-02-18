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


VALID_OBJECTIVE_BODY = """\
# Objective: Test Feature

## Roadmap

### Phase 1: Foundation

### Phase 2: Core Implementation

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infrastructure
  status: done
  plan: null
  pr: '#123'
- id: '1.2'
  description: Add basic tests
  status: in_progress
  plan: '#124'
  pr: null
- id: '1.3'
  description: Update docs
  status: pending
  plan: null
  pr: null
- id: '2.1'
  description: Build main feature
  status: done
  plan: null
  pr: '#125'
- id: '2.2'
  description: Add integration tests
  status: blocked
  plan: null
  pr: null
- id: '2.3'
  description: Performance tuning
  status: skipped
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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
    assert output["summary"]["total_nodes"] == 6
    assert output["summary"]["done"] == 2
    assert output["summary"]["in_progress"] == 1
    assert output["summary"]["pending"] == 1
    assert output["summary"]["blocked"] == 1
    assert output["summary"]["skipped"] == 1
    assert output["next_node"]["id"] == "1.3"
    assert output["all_complete"] is False


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
    """Test that a done step without PR reference is flagged."""
    body = """\
# Objective: All Done

## Roadmap

### Phase 1: Done

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: First
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Second
  status: done
  plan: null
  pr: '#101'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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
    body = """\
# Objective: Sequential

## Roadmap

### Phase 1: First

### Phase 2: Second

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Step one
  status: pending
  plan: null
  pr: null
- id: '2.1'
  description: Step two
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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
    body = """\
# Objective: Gaps

## Roadmap

### Phase 1: First

### Phase 3: Third

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Step one
  status: pending
  plan: null
  pr: null
- id: '3.1'
  description: Step three
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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
    body = """\
# Objective: Sub-phases

## Roadmap

### Phase 1A: First Part

### Phase 1B: Second Part

### Phase 2: Core

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: 1A.1
  description: Step one
  status: pending
  plan: null
  pr: null
- id: 1B.1
  description: Step two
  status: pending
  plan: null
  pr: null
- id: '2.1'
  description: Step three
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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
    assert len(result.graph.nodes) == 6
    assert result.summary["total_nodes"] == 6


def test_validate_objective_returns_error_for_missing_issue() -> None:
    """Test that validate_objective returns error type for missing issue."""
    fake_gh = FakeGitHubIssues()

    result = validate_objective(fake_gh, Path("/fake/repo"), 999)

    assert isinstance(result, ObjectiveValidationError)
    assert "999" in result.error


def test_all_steps_complete_json() -> None:
    """Test JSON output when all steps are done (for closing trigger detection)."""
    body = """\
# Objective: Complete

## Roadmap

### Phase 1: Done

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: First
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Second
  status: skipped
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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
    assert output["next_node"] is None
    assert output["all_complete"] is True


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
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Set up project structure
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Add core types
  status: pending
  plan: null
  pr: null
```

</details>
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
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Set up project structure
  status: done
  plan: null
  pr: '#100'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


def test_v2_valid_header_passes_check_6() -> None:
    """v2 format: objective-header with objective_comment_id passes Check 6."""
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


def test_v2_missing_comment_id_fails_check_6() -> None:
    """v2 format: objective-header without objective_comment_id fails Check 6."""
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


def test_plan_ref_missing_hash_prefix_fails() -> None:
    """Test that plan reference without '#' prefix is flagged by Check 7."""
    body = """\
# Objective: Bad Ref

## Roadmap

### Phase 1: Work

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: First step
  status: in_progress
  plan: '7146'
  pr: null
- id: '1.2'
  description: Second step
  status: done
  plan: null
  pr: '#100'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""
    issue = _make_issue(1700, "Objective: Bad Ref", body)
    fake_gh = FakeGitHubIssues(issues={1700: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1700"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "missing '#' prefix" in result.output


def test_pr_ref_missing_hash_prefix_fails() -> None:
    """Test that PR reference without '#' prefix is flagged by Check 7."""
    body = """\
# Objective: Bad PR Ref

## Roadmap

### Phase 1: Work

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: First step
  status: done
  plan: null
  pr: '100'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""
    issue = _make_issue(1800, "Objective: Bad PR Ref", body)
    fake_gh = FakeGitHubIssues(issues={1800: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1800"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "missing '#' prefix" in result.output


def test_done_step_with_plan_and_pr_passes() -> None:
    """Test that a done step with both plan and PR references passes Check 3."""
    body = """\
# Objective: Done With Plan

## Roadmap

### Phase 1: Work

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: First step
  status: done
  plan: '#1234'
  pr: '#5678'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""
    issue = _make_issue(2000, "Objective: Done With Plan", body)
    fake_gh = FakeGitHubIssues(issues={2000: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["2000"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "[FAIL]" not in result.output
    assert "Status/PR consistency" in result.output


def test_valid_hash_prefix_refs_pass() -> None:
    """Test that properly prefixed plan/PR references pass Check 7."""
    issue = _make_issue(1900, "Objective: Good Refs", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={1900: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["1900"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    assert "Plan/PR references use '#' prefix" in result.output
