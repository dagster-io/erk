"""Unit tests for update_plan_objective exec CLI command.

Tests GitHub issue plan-header objective_issue updates.
Uses real GitHubPlanStore with FakeGitHubIssues for testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_plan_objective import (
    update_plan_objective,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block


def make_plan_header_body(
    schema_version: str = "2",
    created_at: str = "2025-11-25T14:37:43.513418+00:00",
    created_by: str = "testuser",
    worktree_name: str = "test-worktree",
    objective_issue: int | None = None,
) -> str:
    """Create a test issue body with plan-header metadata block."""
    objective_line = (
        f"objective_issue: {objective_issue}"
        if objective_issue is not None
        else "objective_issue: null"
    )

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '{schema_version}'
created_at: '{created_at}'
created_by: {created_by}
worktree_name: {worktree_name}
{objective_line}

```

</details>
<!-- /erk:metadata-block:plan-header -->

Some extra content after the block."""


def make_issue_info(number: int, body: str) -> IssueInfo:
    """Create test IssueInfo with given number and body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Issue",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_update_plan_objective_success() -> None:
    """Test successful objective_issue update."""
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={123: make_issue_info(123, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_plan_objective,
        ["123", "7823"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["objective_issue"] == 7823

    # Verify issue body was updated with objective_issue
    updated_issue = fake_gh.get_issue(Path(), 123)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["objective_issue"] == 7823


def test_update_plan_objective_overwrites_existing() -> None:
    """Test that objective_issue update overwrites existing value."""
    body = make_plan_header_body(objective_issue=1000)
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    runner = CliRunner()

    result = runner.invoke(
        update_plan_objective,
        ["456", "7823"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify existing value was overwritten
    updated_issue = fake_gh.get_issue(Path(), 456)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["objective_issue"] == 7823


# ============================================================================
# Error Cases
# ============================================================================


def test_update_plan_objective_issue_not_found() -> None:
    """Test error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_plan_objective,
        ["999", "7823"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "github-api-failed"
    assert "999" in output["message"]


def test_update_plan_objective_no_plan_header_block() -> None:
    """Test error when issue has no plan-header block (old format)."""
    old_format_body = """# Old Format Issue

This is an issue created before plan-header blocks were introduced.
"""
    fake_gh = FakeGitHubIssues(issues={100: make_issue_info(100, old_format_body)})
    runner = CliRunner()

    result = runner.invoke(
        update_plan_objective,
        ["100", "7823"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "github-api-failed"


def test_update_plan_objective_zero_number() -> None:
    """Test LBYL rejection of non-positive objective_issue_number."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_plan_objective,
        ["123", "0"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid-input"
    assert "positive" in output["message"]
