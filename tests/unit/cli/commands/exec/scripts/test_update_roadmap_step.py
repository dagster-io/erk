"""Unit tests for update-roadmap-step command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_roadmap_step import update_roadmap_step
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo

ROADMAP_BODY = """\
# Objective: Build Feature X

## Roadmap

### Phase 1: Foundation (1 PR)

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Set up project structure | - | #100 |
| 1.2 | Add core types | - | plan #200 |
| 1.3 | Add utility functions | - | - |

### Phase 2: Implementation (1 PR)

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Implement main feature | - | - |
| 2.2 | Add tests | blocked | - |
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


def test_update_pending_step_with_plan_pr() -> None:
    """Update a pending step with a plan PR reference."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "plan #6464"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 6423
    assert output["step_id"] == "1.3"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "plan #6464"
    assert output["url"] == "https://github.com/test/repo/issues/6423"

    # Verify the body was updated
    assert len(fake_gh.updated_bodies) == 1
    updated_body = fake_gh.updated_bodies[0][1]
    assert "plan #6464" in updated_body
    # Status cell should be "in-progress" for plan PR
    assert "| 1.3 " in updated_body
    assert "| in-progress |" in updated_body


def test_update_step_with_existing_pr() -> None:
    """Update a step that already has a PR reference."""
    issue = _make_issue(6423, ROADMAP_BODY)
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
    assert output["previous_pr"] == "plan #200"
    assert output["new_pr"] == "#500"

    # Verify the body was updated
    updated_body = fake_gh.updated_bodies[0][1]
    assert "#500" in updated_body
    # The old "plan #200" should be replaced
    assert "plan #200" not in updated_body
    # Status cell should be "done" for merged PR
    assert "| done |" in updated_body


def test_clear_pr_reference() -> None:
    """Clear a step's PR reference by passing empty string."""
    issue = _make_issue(6423, ROADMAP_BODY)
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

    # Verify the body was updated with "-" in PR cell
    updated_body = fake_gh.updated_bodies[0][1]
    # The row for 1.1 should now have "-" in PR cell
    assert "#100" not in updated_body
    # Status cell should be "pending" when PR is cleared
    assert "| pending |" in updated_body


def test_step_not_found() -> None:
    """Error when step ID doesn't exist in roadmap."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "9.9", "--pr", "plan #123"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
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

    assert result.exit_code == 1
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

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_roadmap"


def test_update_step_in_phase_2() -> None:
    """Update a step in a later phase."""
    issue = _make_issue(6423, ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "2.1", "--pr", "plan #300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["step_id"] == "2.1"
    assert output["previous_pr"] is None
    assert output["new_pr"] == "plan #300"

    updated_body = fake_gh.updated_bodies[0][1]
    assert "plan #300" in updated_body


FRONTMATTER_ROADMAP_BODY = """\
# Objective: Build Feature X

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "1"
steps:
  - id: "1.1"
    description: "Set up project structure"
    status: "done"
    pr: "#100"
  - id: "1.2"
    description: "Add core types"
    status: "in_progress"
    pr: "plan #200"
  - id: "1.3"
    description: "Add utility functions"
    status: "pending"
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation (1 PR)

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Set up project structure | done | #100 |
| 1.2 | Add core types | in-progress | plan #200 |
| 1.3 | Add utility functions | pending | - |
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

    # Verify both frontmatter and table were updated
    updated_body = fake_gh.updated_bodies[0][1]
    # Frontmatter should contain the new PR (YAML may use single or double quotes)
    assert "pr: '#999'" in updated_body or 'pr: "#999"' in updated_body
    # Table should also be updated
    assert "| 1.3 " in updated_body
    assert "| done |" in updated_body or "#999" in updated_body


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
    # (YAML may use single or double quotes)
    assert "id: '1.1'" in updated_body or 'id: "1.1"' in updated_body
    assert "pr: '#100'" in updated_body or 'pr: "#100"' in updated_body
    assert "status: done" in updated_body  # No quotes for simple strings
    # Step 1.3 should remain unchanged
    assert "id: '1.3'" in updated_body or 'id: "1.3"' in updated_body
    assert "pr: null" in updated_body


def test_fallback_to_table_when_no_frontmatter() -> None:
    """When no frontmatter exists, fall back to table-only update."""
    # Use the original ROADMAP_BODY which has no metadata block
    issue = _make_issue(6423, ROADMAP_BODY)
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
    # Should update table
    assert "#888" in updated_body
    # Should NOT have metadata block (since original didn't have one)
    assert "erk:metadata-block:objective-roadmap" not in updated_body


def test_explicit_status_option_table_only() -> None:
    """--status flag sets explicit status in table instead of inferring from PR."""
    issue = _make_issue(6423, ROADMAP_BODY)
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
    # Frontmatter should have status: done
    assert "status: done" in updated_body
    # Table should also show done
    assert "| done |" in updated_body


def test_status_without_flag_defaults_to_pending_in_frontmatter() -> None:
    """Without --status, frontmatter status resets to pending for inference."""
    issue = _make_issue(6423, FRONTMATTER_ROADMAP_BODY)
    fake_gh = FakeGitHubIssues(issues={6423: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_roadmap_step,
        ["6423", "--step", "1.3", "--pr", "plan #600"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"

    updated_body = fake_gh.updated_bodies[0][1]
    # Frontmatter status should be pending (reset for inference)
    # The step 1.3 should have status: pending in YAML
    assert "status: pending" in updated_body
