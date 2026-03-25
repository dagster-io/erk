"""Unit tests for get-prs-for-objective command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_prs_for_objective import (
    get_prs_for_objective,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues


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
        labels=["erk-pr"],
        assignees=[],
        created_at=fixed_time,
        updated_at=fixed_time,
        author="testuser",
    )


def test_get_prs_for_objective_returns_empty_list() -> None:
    """Test fetch with no prs linked to objective."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_prs_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["objective_number"] == 4954
    assert output["prs"] == []


def test_get_prs_for_objective_finds_linked_prs() -> None:
    """Test fetch with prs linked to objective."""
    # PR linked to objective 4954
    pr_linked = _make_issue(
        number=5066,
        title="P5066: Implement feature X",
        body=_make_plan_header(objective_id=4954),
    )
    # PR linked to different objective
    pr_other = _make_issue(
        number=5067,
        title="P5067: Other plan",
        body=_make_plan_header(objective_id=9999),
    )
    # PR with no objective
    pr_no_obj = _make_issue(
        number=5068,
        title="P5068: Standalone plan",
        body=_make_plan_header(objective_id=None),
    )

    fake_gh = FakeGitHubIssues(
        issues={
            5066: pr_linked,
            5067: pr_other,
            5068: pr_no_obj,
        }
    )
    runner = CliRunner()

    result = runner.invoke(
        get_prs_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["objective_number"] == 4954
    assert len(output["prs"]) == 1
    assert output["prs"][0] == {
        "number": 5066,
        "state": "OPEN",
        "title": "P5066: Implement feature X",
    }


def test_get_prs_for_objective_finds_multiple_prs() -> None:
    """Test fetch with multiple prs linked to same objective."""
    pr1 = _make_issue(
        number=5066,
        title="P5066: Phase 1",
        body=_make_plan_header(objective_id=4954),
        state="CLOSED",
    )
    pr2 = _make_issue(
        number=5067,
        title="P5067: Phase 2",
        body=_make_plan_header(objective_id=4954),
        state="OPEN",
    )

    fake_gh = FakeGitHubIssues(
        issues={
            5066: pr1,
            5067: pr2,
        }
    )
    runner = CliRunner()

    result = runner.invoke(
        get_prs_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["prs"]) == 2

    # Extract numbers for verification (order may vary)
    pr_numbers = {p["number"] for p in output["prs"]}
    assert pr_numbers == {5066, 5067}


def test_get_prs_for_objective_supports_legacy_field() -> None:
    """Test fetch supports legacy objective_issue field name."""
    pr_legacy = _make_issue(
        number=5066,
        title="P5066: Legacy plan",
        body=_make_plan_header(objective_id=4954, use_legacy_field=True),
    )

    fake_gh = FakeGitHubIssues(issues={5066: pr_legacy})
    runner = CliRunner()

    result = runner.invoke(
        get_prs_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["prs"]) == 1
    assert output["prs"][0]["number"] == 5066


def test_get_prs_for_objective_skips_prs_without_metadata() -> None:
    """Test that prs without plan-header block are skipped."""
    # PR with no metadata block
    pr_no_metadata = _make_issue(
        number=5066,
        title="P5066: Old format plan",
        body="# Old Plan\n\nNo metadata block here.",
    )

    fake_gh = FakeGitHubIssues(issues={5066: pr_no_metadata})
    runner = CliRunner()

    result = runner.invoke(
        get_prs_for_objective,
        ["4954"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["prs"] == []


def test_json_output_structure() -> None:
    """Test JSON output structure contains expected fields."""
    pr = _make_issue(
        number=5066,
        title="P5066: Test",
        body=_make_plan_header(objective_id=100),
    )
    fake_gh = FakeGitHubIssues(issues={5066: pr})
    runner = CliRunner()

    result = runner.invoke(
        get_prs_for_objective,
        ["100"],
        obj=ErkContext.for_test(github=FakeLocalGitHub(issues_gateway=fake_gh)),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level keys
    assert "success" in output
    assert "objective_number" in output
    assert "prs" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["objective_number"], int)
    assert isinstance(output["prs"], list)

    # Verify PR structure
    pr_data = output["prs"][0]
    assert "number" in pr_data
    assert "state" in pr_data
    assert "title" in pr_data
