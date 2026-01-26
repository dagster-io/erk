"""Unit tests for get_plan_metadata exec command.

Tests GitHub issue plan-header metadata extraction.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_plan_metadata import get_plan_metadata
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def make_plan_header_body(
    schema_version: str = "2",
    created_at: str = "2025-11-25T14:37:43.513418+00:00",
    created_by: str = "testuser",
    worktree_name: str = "test-worktree",
    objective_issue: int | None = 3400,
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
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


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


def test_get_plan_metadata_returns_existing_field() -> None:
    """Test successful extraction of an existing field."""
    body = make_plan_header_body(objective_issue=3400)
    fake_gh = FakeGitHubIssues(issues={3509: make_issue_info(3509, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["3509", "objective_issue"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] == 3400
    assert output["issue_number"] == 3509
    assert output["field"] == "objective_issue"


def test_get_plan_metadata_returns_string_field() -> None:
    """Test extraction of a string field value."""
    body = make_plan_header_body(worktree_name="P3509-feature-xyz")
    fake_gh = FakeGitHubIssues(issues={3509: make_issue_info(3509, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["3509", "worktree_name"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] == "P3509-feature-xyz"
    assert output["field"] == "worktree_name"


def test_get_plan_metadata_returns_null_for_nonexistent_field() -> None:
    """Test that a nonexistent field returns null, not an error."""
    body = make_plan_header_body()
    fake_gh = FakeGitHubIssues(issues={3509: make_issue_info(3509, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["3509", "nonexistent_field"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] is None
    assert output["field"] == "nonexistent_field"


def test_get_plan_metadata_returns_null_for_null_field() -> None:
    """Test that a field explicitly set to null returns null."""
    body = make_plan_header_body(objective_issue=None)
    fake_gh = FakeGitHubIssues(issues={3509: make_issue_info(3509, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["3509", "objective_issue"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] is None
    assert output["field"] == "objective_issue"


def test_get_plan_metadata_no_plan_header_block() -> None:
    """Test that an issue without plan-header block returns null."""
    old_format_body = """# Old Format Issue

This is an issue created before plan-header blocks were introduced.
"""
    fake_gh = FakeGitHubIssues(issues={100: make_issue_info(100, old_format_body)})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["100", "objective_issue"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Should succeed with null value, not error
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] is None
    assert output["field"] == "objective_issue"


# ============================================================================
# Error Cases
# ============================================================================


def test_get_plan_metadata_issue_not_found() -> None:
    """Test error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["9999", "objective_issue"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "#9999" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success() -> None:
    """Test JSON output structure on success."""
    body = make_plan_header_body(objective_issue=3400)
    fake_gh = FakeGitHubIssues(issues={321: make_issue_info(321, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["321", "objective_issue"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "value" in output
    assert "issue_number" in output
    assert "field" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["field"], str)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == 321
    assert output["field"] == "objective_issue"
    assert output["value"] == 3400


def test_json_output_structure_error() -> None:
    """Test JSON output structure on error."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_metadata,
        ["999", "objective_issue"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)

    # Verify values
    assert output["success"] is False
