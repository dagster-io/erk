"""Unit tests for update-roadmap-step command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_roadmap_step import update_roadmap_step
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

ROADMAP_BODY_5COL = """\
# Objective: Build Feature X

## Roadmap

### Phase 1: Foundation (1 PR)

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project structure | done | - | #100 |
| 1.2 | Add core types | in-progress | #200 | - |
| 1.3 | Add utility functions | pending | - | - |

### Phase 2: Implementation (1 PR)

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Implement main feature | pending | - | - |
| 2.2 | Add tests | blocked | - | - |
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


def test_update_pending_step_with_plan() -> None:
    """Update a pending step with a plan reference using --plan."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6423
    assert output["step_id"] == "1.3"
    assert output["previous_plan"] is None
    assert output["new_plan"] == "#6464"
    assert output["url"] == "https://github.com/test/repo/issues/6423"

    # Verify the body was updated with 5-col format
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "#6464" in updated_body
    assert "| in-progress |" in updated_body


def test_update_step_with_pr() -> None:
    """Update a step with a PR reference (auto-clears plan)."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
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
    assert output["previous_plan"] == "#200"
    assert output["new_pr"] == "#500"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    assert "| done |" in updated_body


def test_clear_pr_reference() -> None:
    """Clear a step's PR reference by passing empty string."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
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

    updated_body = fake_gh.updated_bodies[0][1]
    assert "| pending |" in updated_body


def test_step_not_found() -> None:
    """Error when step ID doesn't exist in roadmap."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "9.9", "--plan", "#123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
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

    assert result.exit_code == 0
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

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


def test_update_step_in_phase_2() -> None:
    """Update a step in a later phase."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "2.1", "--plan", "#300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["step_id"] == "2.1"
    assert output["previous_plan"] is None
    assert output["new_plan"] == "#300"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#300" in updated_body


FRONTMATTER_ROADMAP_BODY = """\
# Objective: Build Feature X

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
    status: "in_progress"
    plan: "#200"
    pr: null
  - id: "1.3"
    description: "Add utility functions"
    status: "pending"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation (1 PR)

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Set up project structure | done | - | #100 |
| 1.2 | Add core types | in-progress | #200 | - |
| 1.3 | Add utility functions | pending | - | - |
"""


def test_update_with_frontmatter() -> None:
    """Update step when frontmatter is present updates both YAML and table."""
    issue = _make_issue(6423, FRONTMATTER_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["new_pr"] == "#999"

    updated_body = fake_gh.updated_bodies[0][1]
    # Frontmatter should contain the new PR
    assert "pr: '#999'" in updated_body or 'pr: "#999"' in updated_body
    # Table should also be updated
    assert "| 1.3 " in updated_body


def test_update_with_frontmatter_preserves_other_steps() -> None:
    """Update with frontmatter preserves other steps' data."""
    issue = _make_issue(6423, FRONTMATTER_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.2", "--pr", "#777"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    updated_body = fake_gh.updated_bodies[0][1]

    # Original step 1.1 should remain unchanged in frontmatter
    assert "id: '1.1'" in updated_body or 'id: "1.1"' in updated_body
    assert "pr: '#100'" in updated_body or 'pr: "#100"' in updated_body
    assert "status: done" in updated_body


def test_fallback_to_table_when_no_frontmatter() -> None:
    """When no frontmatter exists, fall back to table-only update."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#888"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#888" in updated_body
    assert "erk:metadata-block:objective-roadmap" not in updated_body


def test_explicit_status_option_table_only() -> None:
    """--status flag sets explicit status in table instead of inferring."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#500", "--status", "done"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    assert "| done |" in updated_body


def test_explicit_status_option_with_frontmatter() -> None:
    """--status flag sets explicit status in both frontmatter and table."""
    issue = _make_issue(6423, FRONTMATTER_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#500", "--status", "done"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "status: done" in updated_body
    assert "| done |" in updated_body


def test_update_multiple_steps_success() -> None:
    """Update multiple steps in a single operation — all succeed."""
    issue = _make_issue(6697, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.2", "--step", "1.3", "--step", "2.1", "--plan", "#6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6697
    assert output["new_plan"] == "#6759"
    assert output["url"] == "https://github.com/test/repo/issues/6697"

    assert "steps" in output
    assert len(output["steps"]) == 3

    step_1_2 = next(s for s in output["steps"] if s["step_id"] == "1.2")
    assert step_1_2["success"] is True
    assert step_1_2["previous_plan"] == "#200"

    step_1_3 = next(s for s in output["steps"] if s["step_id"] == "1.3")
    assert step_1_3["success"] is True
    assert step_1_3["previous_plan"] is None

    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("#6759") == 3


def test_update_multiple_steps_partial_failure() -> None:
    """Multi-step update rejected upfront when any step is missing."""
    issue = _make_issue(6697, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.2", "--step", "9.9", "--step", "2.1", "--plan", "#6759"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["issue_number"] == 6697

    assert len(output["steps"]) == 1
    assert output["steps"][0]["step_id"] == "9.9"
    assert output["steps"][0]["success"] is False

    assert len(fake_gh.updated_bodies) == 0


def test_build_output_multi_step_and_semantics() -> None:
    """_build_output uses AND semantics: success=false when any step fails.

    Tests the batch success semantics directly. The processing loop's
    replacement_failed path is defensive (parse_roadmap and
    _replace_step_refs_in_body use the same underlying parsing), so we
    verify AND semantics through _build_output with mixed results.
    """
    from erk.cli.commands.exec.scripts.update_roadmap_step import _build_output

    results: list[dict[str, object]] = [
        {"step_id": "1.2", "success": True, "previous_plan": "#200", "previous_pr": None},
        {"step_id": "1.3", "success": False, "error": "replacement_failed"},
    ]
    output = _build_output(
        issue_number=6697,
        step=("1.2", "1.3"),
        plan_value="#6759",
        pr_value=None,
        url="https://github.com/test/repo/issues/6697",
        results=results,
        include_body=False,
        updated_body=None,
    )

    # AND semantics: success=false because step 1.3 failed
    assert output["success"] is False
    assert output["issue_number"] == 6697
    steps = output["steps"]
    assert isinstance(steps, list)
    assert len(steps) == 2


def test_update_multiple_steps_same_phase() -> None:
    """Update multiple steps within the same phase."""
    issue = _make_issue(6697, ROADMAP_BODY_5COL)
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

    assert len(output["steps"]) == 3
    for step_result in output["steps"]:
        assert step_result["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert updated_body.count("#555") == 3
    assert updated_body.count("| done |") >= 3


def test_single_step_maintains_legacy_output_format() -> None:
    """Single --step usage maintains backward-compatible output format."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--plan", "#6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    # Should use legacy format (no "steps" array)
    assert "steps" not in output
    assert output["success"] is True
    assert output["step_id"] == "1.3"
    assert output["previous_plan"] is None
    assert output["new_plan"] == "#6464"


def test_missing_ref_error() -> None:
    """Error when neither --plan nor --pr is provided."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_ref"


def test_include_body_flag_single_step() -> None:
    """--include-body includes updated_body in JSON output for single step."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#500", "--include-body"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" in output
    assert "#500" in output["updated_body"]
    assert "| done |" in output["updated_body"]


def test_include_body_flag_multiple_steps() -> None:
    """--include-body includes updated_body with all step mutations applied."""
    issue = _make_issue(6697, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6697: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6697", "--step", "1.2", "--step", "1.3", "--pr", "#555", "--include-body"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" in output
    # Both steps should be reflected in the body
    assert output["updated_body"].count("#555") == 2


def test_include_body_not_set_by_default() -> None:
    """updated_body field is absent when --include-body is not passed."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#500"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "updated_body" not in output


def test_none_plan_preserves_existing_value() -> None:
    """_replace_step_refs_in_body with new_plan=None preserves existing plan."""
    from erk.cli.commands.exec.scripts.update_roadmap_step import _replace_step_refs_in_body

    body = ROADMAP_BODY_5COL
    # Step 1.2 has plan=#200
    result = _replace_step_refs_in_body(
        body, "1.2", new_plan=None, new_pr="#500", explicit_status=None
    )

    assert result is not None
    # Plan should be preserved (not cleared)
    assert "#200" in result
    # PR should be updated
    assert "#500" in result


def test_none_pr_preserves_existing_value() -> None:
    """_replace_step_refs_in_body with new_pr=None preserves existing PR."""
    from erk.cli.commands.exec.scripts.update_roadmap_step import _replace_step_refs_in_body

    body = ROADMAP_BODY_5COL
    # Step 1.1 has pr=#100
    result = _replace_step_refs_in_body(
        body, "1.1", new_plan=None, new_pr=None, explicit_status="planning"
    )

    assert result is not None
    # PR should be preserved
    assert "#100" in result
    assert "| planning |" in result


def test_empty_string_clears_value() -> None:
    """_replace_step_refs_in_body with empty string clears to '-'."""
    from erk.cli.commands.exec.scripts.update_roadmap_step import _replace_step_refs_in_body

    body = ROADMAP_BODY_5COL
    # Step 1.2 has plan=#200, pr=-
    result = _replace_step_refs_in_body(body, "1.2", new_plan="", new_pr=None, explicit_status=None)

    assert result is not None
    # Plan should be cleared, PR preserved (was already "-")
    # After clearing plan and preserving pr="-", status should be pending
    assert "| pending |" in result


def test_planning_status_via_explicit_status() -> None:
    """update-roadmap-step with --status planning sets planning status."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "#200", "--status", "planning"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    updated_body = fake_gh.updated_bodies[0][1]
    assert "| planning |" in updated_body
    assert "#200" in updated_body


def test_include_body_on_failure() -> None:
    """updated_body field is absent on failure even with --include-body."""
    issue = _make_issue(6423, ROADMAP_BODY_5COL)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "9.9", "--pr", "#500", "--include-body"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert "updated_body" not in output
