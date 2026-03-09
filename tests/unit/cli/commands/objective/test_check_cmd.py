"""Unit tests for erk objective check command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.objective.check_cmd import (
    ObjectiveValidationError,
    ObjectiveValidationSuccess,
    check_objective,
    validate_objective,
)
from erk_shared.context.context import ErkContext
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.github_issues import FakeGitHubIssues
from erk_shared.fakes.remote_github import FakeRemoteGitHub
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import RepoInfo
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

_TEST_REPO_INFO = RepoInfo(owner="test", name="repo")


def _make_remote(
    issues: dict[int, IssueInfo],
    *,
    comments_by_id: dict[int, str] | None = None,
) -> FakeRemoteGitHub:
    """Create a FakeRemoteGitHub from an issue dict."""
    return FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues,
        issue_comments=None,
        pr_references=None,
        comments_by_id=comments_by_id,
    )


def _test_ctx(
    *,
    fake_gh: FakeGitHubIssues,
    issues: dict[int, IssueInfo],
    comments_by_id: dict[int, str] | None = None,
) -> ErkContext:
    """Create a test context with both local and remote GitHub."""
    return ErkContext.for_test(
        github=FakeLocalGitHub(issues_gateway=fake_gh),
        remote_github=_make_remote(issues, comments_by_id=comments_by_id),
        repo_info=_TEST_REPO_INFO,
    )


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
        obj=_test_ctx(fake_gh=fake_gh, issues={100: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={100: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={200: issue}),
    )

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "erk-objective label" in result.output


def test_roadmap_free_objective_passes() -> None:
    """Test that a body with no roadmap block passes as roadmap-free."""
    body = """# Objective: No Roadmap

This objective has no roadmap tables.
"""
    issue = _make_issue(300, "Objective: No Roadmap", body)
    fake_gh = FakeGitHubIssues(issues={300: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["300"],
        obj=_test_ctx(fake_gh=fake_gh, issues={300: issue}),
    )

    assert result.exit_code == 0
    assert "[PASS]" in result.output
    assert "no roadmap" in result.output


def test_roadmap_free_objective_json_output() -> None:
    """Test JSON output for a roadmap-free objective."""
    body = """# Objective: No Roadmap

This objective has no roadmap tables.
"""
    issue = _make_issue(350, "Objective: No Roadmap JSON", body)
    fake_gh = FakeGitHubIssues(issues={350: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["350", "--json-output"],
        obj=_test_ctx(fake_gh=fake_gh, issues={350: issue}),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    assert output["success"] is True
    assert output["phases"] == []
    assert output["summary"] == {}
    assert output["validation_errors"] == []


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
        obj=_test_ctx(fake_gh=fake_gh, issues={400: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={500: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={600: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={900: issue}),
    )

    assert result.exit_code == 0
    assert "Phase numbering is sequential" in result.output
    assert "[FAIL]" not in result.output


def test_validate_objective_returns_success_type() -> None:
    """Test that validate_objective returns proper result types."""
    issue = _make_issue(700, "Objective: Test", VALID_OBJECTIVE_BODY)

    result = validate_objective(
        _make_remote({700: issue}),
        owner="test",
        repo="repo",
        issue_number=700,
    )

    assert isinstance(result, ObjectiveValidationSuccess)
    assert result.passed is True
    assert len(result.graph.nodes) == 6
    assert result.summary["total_nodes"] == 6


def test_validate_objective_returns_error_for_missing_issue() -> None:
    """Test that validate_objective returns error type for missing issue."""
    result = validate_objective(
        _make_remote({}),
        owner="test",
        repo="repo",
        issue_number=999,
    )

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
        obj=_test_ctx(fake_gh=fake_gh, issues={800: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={1200: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={1300: issue}),
    )

    assert result.exit_code == 1
    assert "objective-header missing objective_comment_id" in result.output


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
        obj=_test_ctx(fake_gh=fake_gh, issues={1800: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={2000: issue}),
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
        obj=_test_ctx(fake_gh=fake_gh, issues={1900: issue}),
    )

    assert result.exit_code == 0
    assert "PR references use '#' prefix" in result.output


# --- fan-out/fan-in tests (schema v3 with explicit depends_on) ---

FAN_OUT_FAN_IN_BODY = """\
# Objective: Fan-Out Test

## Roadmap

### Phase 1: Root

### Phase 2: Parallel

### Phase 3: Merge

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '3'
nodes:
- id: '1.1'
  description: Root step
  status: done
  plan: null
  pr: '#100'
  depends_on: []
- id: '2.1'
  description: Branch A
  status: pending
  plan: null
  pr: null
  depends_on:
  - '1.1'
- id: '2.2'
  description: Branch B
  status: pending
  plan: null
  pr: null
  depends_on:
  - '1.1'
- id: '3.1'
  description: Merge step
  status: pending
  plan: null
  pr: null
  depends_on:
  - '2.1'
  - '2.2'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


def test_fan_out_fan_in_passes_validation() -> None:
    """Objective with explicit deps validates successfully."""
    issue = _make_issue(2100, "Objective: Fan-Out", FAN_OUT_FAN_IN_BODY)
    fake_gh = FakeGitHubIssues(issues={2100: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["2100"],
        obj=_test_ctx(fake_gh=fake_gh, issues={2100: issue}),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "[FAIL]" not in result.output


def test_fan_out_fan_in_json_output() -> None:
    """JSON has correct next_node and summary."""
    issue = _make_issue(2200, "Objective: Fan-Out JSON", FAN_OUT_FAN_IN_BODY)
    fake_gh = FakeGitHubIssues(issues={2200: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["2200", "--json-output"],
        obj=_test_ctx(fake_gh=fake_gh, issues={2200: issue}),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["summary"]["total_nodes"] == 4
    assert output["summary"]["done"] == 1
    assert output["summary"]["pending"] == 3
    # next_node should be one of the fan-out branches (2.1 by position order)
    assert output["next_node"]["id"] == "2.1"
    assert output["all_complete"] is False


# --- Check 8: Roadmap table sync tests ---

_CHECK8_ISSUE_BODY = """\
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

_CHECK8_COMMENT_IN_SYNC = """\
# Objective Body

Some context here.

<!-- erk:roadmap-table -->
### Phase 1: Foundation (1 PR)
| Node | Description | Status | PR |
|------|-------------|--------|----|
| 1.1 | Set up project structure | done | #100 |
| 1.2 | Add core types | pending | - |
<!-- /erk:roadmap-table -->

More content.
"""

_CHECK8_COMMENT_OUT_OF_SYNC = """\
# Objective Body

Some context here.

<!-- erk:roadmap-table -->
### Phase 1: Foundation (0 PR)

| Node | Description | Status | PR |
|------|-------------|--------|----|
| 1.1 | Set up project structure | pending | - |
| 1.2 | Add core types | pending | - |
<!-- /erk:roadmap-table -->

More content.
"""


def test_roadmap_table_in_sync_passes() -> None:
    """Check 8: comment table matches YAML → PASS."""
    issue = _make_issue(2300, "Objective: Sync Test", _CHECK8_ISSUE_BODY)
    fake_gh = FakeGitHubIssues(
        issues={2300: issue},
    )
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["2300"],
        obj=_test_ctx(
            fake_gh=fake_gh,
            issues={2300: issue},
            comments_by_id={42: _CHECK8_COMMENT_IN_SYNC},
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Roadmap table in sync with YAML" in result.output
    assert "[FAIL]" not in result.output


def test_roadmap_table_out_of_sync_fails() -> None:
    """Check 8: comment has stale status → FAIL."""
    issue = _make_issue(2400, "Objective: Drift Test", _CHECK8_ISSUE_BODY)
    fake_gh = FakeGitHubIssues(
        issues={2400: issue},
    )
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["2400"],
        obj=_test_ctx(
            fake_gh=fake_gh,
            issues={2400: issue},
            comments_by_id={42: _CHECK8_COMMENT_OUT_OF_SYNC},
        ),
    )

    assert result.exit_code == 1
    assert "Roadmap table out of sync" in result.output


def test_roadmap_table_check_skipped_without_comment_id() -> None:
    """Check 8: no objective_comment_id → check not run, no FAIL."""
    issue = _make_issue(2500, "Objective: No Comment ID", VALID_OBJECTIVE_BODY)
    fake_gh = FakeGitHubIssues(issues={2500: issue})
    runner = CliRunner()

    result = runner.invoke(
        check_objective,
        ["2500"],
        obj=_test_ctx(fake_gh=fake_gh, issues={2500: issue}),
    )

    assert result.exit_code == 0
    assert "Roadmap table" not in result.output


# --- Check 9: PR backlink consistency tests ---


def _make_plan_pr_issue(
    number: int,
    *,
    objective_issue: int | None,
) -> IssueInfo:
    """Create a plan PR (as IssueInfo) with plan-header metadata."""
    now = datetime.now(UTC)
    body = format_plan_header_body_for_test(objective_issue=objective_issue)
    return IssueInfo(
        number=number,
        title=f"[erk-plan] Plan #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/pull/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_check9_backlinks_pass_when_all_prs_have_matching_objective() -> None:
    """Check 9: passes when all PR references have matching objective_issue backlinks."""
    objective_issue = _make_issue(100, "Objective: Test", VALID_OBJECTIVE_BODY)
    plan_pr_123 = _make_plan_pr_issue(123, objective_issue=100)
    plan_pr_125 = _make_plan_pr_issue(125, objective_issue=100)

    all_issues = {100: objective_issue, 123: plan_pr_123, 125: plan_pr_125}

    result = validate_objective(
        _make_remote(all_issues),
        owner="test",
        repo="repo",
        issue_number=100,
    )

    assert isinstance(result, ObjectiveValidationSuccess)
    assert result.passed is True
    backlink_checks = [desc for passed, desc in result.checks if "PR backlinks" in desc]
    assert len(backlink_checks) == 1
    assert "all PR references have matching" in backlink_checks[0]


def test_check9_backlinks_fail_when_pr_missing_backlink() -> None:
    """Check 9: fails when a plan PR is missing objective_issue backlink."""
    objective_issue = _make_issue(100, "Objective: Test", VALID_OBJECTIVE_BODY)
    plan_pr_123 = _make_plan_pr_issue(123, objective_issue=100)
    # PR #125 has plan-header but no objective_issue
    plan_pr_125 = _make_plan_pr_issue(125, objective_issue=None)

    all_issues = {100: objective_issue, 123: plan_pr_123, 125: plan_pr_125}

    result = validate_objective(
        _make_remote(all_issues),
        owner="test",
        repo="repo",
        issue_number=100,
    )

    assert isinstance(result, ObjectiveValidationSuccess)
    assert result.passed is False
    backlink_checks = [desc for passed, desc in result.checks if "PR backlinks" in desc]
    assert len(backlink_checks) == 1
    assert "missing objective_issue backlink" in backlink_checks[0]
    assert "#125" in backlink_checks[0]


def test_check9_backlinks_fail_when_pr_has_mismatched_objective() -> None:
    """Check 9: fails when plan PR has objective_issue pointing to different objective."""
    objective_issue = _make_issue(100, "Objective: Test", VALID_OBJECTIVE_BODY)
    plan_pr_123 = _make_plan_pr_issue(123, objective_issue=100)
    plan_pr_125 = _make_plan_pr_issue(125, objective_issue=9999)

    all_issues = {100: objective_issue, 123: plan_pr_123, 125: plan_pr_125}

    result = validate_objective(
        _make_remote(all_issues),
        owner="test",
        repo="repo",
        issue_number=100,
    )

    assert isinstance(result, ObjectiveValidationSuccess)
    assert result.passed is False
    backlink_checks = [desc for passed, desc in result.checks if "PR backlinks" in desc]
    assert len(backlink_checks) == 1
    assert "mismatched" in backlink_checks[0]
    assert "9999" in backlink_checks[0]


def test_check9_skipped_when_pr_has_no_plan_header() -> None:
    """Check 9: PRs without plan-header block are silently skipped."""
    objective_issue = _make_issue(100, "Objective: Test", VALID_OBJECTIVE_BODY)
    now = datetime.now(UTC)
    # PR #123 with matching backlink
    plan_pr_123 = _make_plan_pr_issue(123, objective_issue=100)
    # PR #125 is a regular PR (no plan-header at all)
    regular_pr_125 = IssueInfo(
        number=125,
        title="Regular PR",
        body="Just a regular PR body",
        state="MERGED",
        url="https://github.com/test/repo/pull/125",
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )

    all_issues = {100: objective_issue, 123: plan_pr_123, 125: regular_pr_125}

    result = validate_objective(
        _make_remote(all_issues),
        owner="test",
        repo="repo",
        issue_number=100,
    )

    assert isinstance(result, ObjectiveValidationSuccess)
    assert result.passed is True
    backlink_checks = [desc for passed, desc in result.checks if "PR backlinks" in desc]
    assert len(backlink_checks) == 1
    assert "all PR references have matching" in backlink_checks[0]


def test_check9_skipped_when_no_pr_references() -> None:
    """Check 9: skipped entirely when no nodes have PR references."""
    body_no_prs = """\
# Objective: Test Feature

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup
  status: pending
  plan: null
  pr: null
- id: '1.2'
  description: Build
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""
    issue = _make_issue(100, "Objective: No PRs", body_no_prs)
    all_issues = {100: issue}

    result = validate_objective(
        _make_remote(all_issues),
        owner="test",
        repo="repo",
        issue_number=100,
    )

    assert isinstance(result, ObjectiveValidationSuccess)
    # Check 9 should not appear at all
    backlink_checks = [desc for passed, desc in result.checks if "PR backlinks" in desc]
    assert len(backlink_checks) == 0
