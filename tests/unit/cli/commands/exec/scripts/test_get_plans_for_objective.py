"""Unit tests for get-plans-for-objective command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_plans_for_objective import (
    get_plans_for_objective,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def _make_plan_header(
    *,
    objective_id: int | None,
    use_legacy_field: bool = False,
) -> str:
    """Create a plan-header metadata block."""
    # Use objective_id (new) or objective_issue (legacy)
    field_name = "objective_issue" if use_legacy_field else "objective_id"
    value = objective_id if objective_id is not None else "null"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
{field_name}: {value}
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Test Plan

This is the plan body.
"""


def _make_issue(
    *,
    number: int,
    title: str,
    body: str,
    state: str = "OPEN",
) -> IssueInfo:
    """Create a test IssueInfo."""
    # Use fixed timestamp for deterministic tests
    fixed_time = datetime(2025, 11, 25, 14, 37, 43, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=fixed_time,
        updated_at=fixed_time,
        author="testuser",
    )


def test_get_plans_for_objective_returns_empty_list() -> None:
    """Test fetch with no plans linked to objective."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_plans_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["objective_number"] == 4954
    assert output["plans"] == []


def test_get_plans_for_objective_finds_linked_plans() -> None:
    """Test fetch with plans linked to objective."""
    # Plan linked to objective 4954
    plan_linked = _make_issue(
        number=5066,
        title="P5066: Implement feature X",
        body=_make_plan_header(objective_id=4954),
    )
    # Plan linked to different objective
    plan_other = _make_issue(
        number=5067,
        title="P5067: Other plan",
        body=_make_plan_header(objective_id=9999),
    )
    # Plan with no objective
    plan_no_obj = _make_issue(
        number=5068,
        title="P5068: Standalone plan",
        body=_make_plan_header(objective_id=None),
    )

    fake_gh = FakeGitHubIssues(
        issues={
            5066: plan_linked,
            5067: plan_other,
            5068: plan_no_obj,
        }
    )
    runner = CliRunner()

    result = runner.invoke(
        get_plans_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["objective_number"] == 4954
    assert len(output["plans"]) == 1
    assert output["plans"][0] == {
        "number": 5066,
        "state": "OPEN",
        "title": "P5066: Implement feature X",
    }


def test_get_plans_for_objective_finds_multiple_plans() -> None:
    """Test fetch with multiple plans linked to same objective."""
    plan1 = _make_issue(
        number=5066,
        title="P5066: Phase 1",
        body=_make_plan_header(objective_id=4954),
        state="CLOSED",
    )
    plan2 = _make_issue(
        number=5067,
        title="P5067: Phase 2",
        body=_make_plan_header(objective_id=4954),
        state="OPEN",
    )

    fake_gh = FakeGitHubIssues(
        issues={
            5066: plan1,
            5067: plan2,
        }
    )
    runner = CliRunner()

    result = runner.invoke(
        get_plans_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["plans"]) == 2

    # Extract numbers for verification (order may vary)
    plan_numbers = {p["number"] for p in output["plans"]}
    assert plan_numbers == {5066, 5067}


def test_get_plans_for_objective_supports_legacy_field() -> None:
    """Test fetch supports legacy objective_issue field name."""
    plan_legacy = _make_issue(
        number=5066,
        title="P5066: Legacy plan",
        body=_make_plan_header(objective_id=4954, use_legacy_field=True),
    )

    fake_gh = FakeGitHubIssues(issues={5066: plan_legacy})
    runner = CliRunner()

    result = runner.invoke(
        get_plans_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["plans"]) == 1
    assert output["plans"][0]["number"] == 5066


def test_get_plans_for_objective_skips_plans_without_metadata() -> None:
    """Test that plans without plan-header block are skipped."""
    # Plan with no metadata block
    plan_no_metadata = _make_issue(
        number=5066,
        title="P5066: Old format plan",
        body="# Old Plan\n\nNo metadata block here.",
    )

    fake_gh = FakeGitHubIssues(issues={5066: plan_no_metadata})
    runner = CliRunner()

    result = runner.invoke(
        get_plans_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plans"] == []


def test_json_output_structure() -> None:
    """Test JSON output structure contains expected fields."""
    plan = _make_issue(
        number=5066,
        title="P5066: Test",
        body=_make_plan_header(objective_id=100),
    )
    fake_gh = FakeGitHubIssues(issues={5066: plan})
    runner = CliRunner()

    result = runner.invoke(
        get_plans_for_objective,
        ["100"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level keys
    assert "success" in output
    assert "objective_number" in output
    assert "plans" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["objective_number"], int)
    assert isinstance(output["plans"], list)

    # Verify plan structure
    plan_data = output["plans"][0]
    assert "number" in plan_data
    assert "state" in plan_data
    assert "title" in plan_data
