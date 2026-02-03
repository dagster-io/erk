"""Unit tests for get_objective_metadata exec command.

Tests GitHub issue objective-header metadata extraction.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_objective_metadata import get_objective_metadata
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def make_objective_header_body(
    schema_version: str = "1",
    parent_objective: int | None = 100,
) -> str:
    """Create a test issue body with objective-header metadata block."""
    parent_line = (
        f"parent_objective: {parent_objective}"
        if parent_objective is not None
        else "parent_objective: null"
    )

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

schema_version: '{schema_version}'
{parent_line}

```

</details>
<!-- /erk:metadata-block:objective-header -->

# Test Objective

Roadmap content..."""


def make_issue_info(number: int, body: str) -> IssueInfo:
    """Create test IssueInfo with given number and body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Objective",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-objective"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_get_objective_metadata_returns_existing_parent() -> None:
    """Test successful extraction of parent_objective field."""
    body = make_objective_header_body(parent_objective=200)
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["456", "parent_objective"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] == 200
    assert output["issue_number"] == 456
    assert output["field"] == "parent_objective"


def test_get_objective_metadata_returns_null_for_nonexistent_field() -> None:
    """Test that a nonexistent field returns null, not an error."""
    body = make_objective_header_body()
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["456", "nonexistent_field"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] is None
    assert output["field"] == "nonexistent_field"


def test_get_objective_metadata_returns_null_for_null_parent() -> None:
    """Test that parent_objective explicitly set to null returns null."""
    body = make_objective_header_body(parent_objective=None)
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["456", "parent_objective"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] is None
    assert output["field"] == "parent_objective"


def test_get_objective_metadata_no_objective_header_block() -> None:
    """Test that an issue without objective-header block returns null."""
    old_format_body = """# Old Format Objective

This is an objective created before objective-header blocks were introduced.
"""
    fake_gh = FakeGitHubIssues(issues={100: make_issue_info(100, old_format_body)})
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["100", "parent_objective"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Should succeed with null value, not error (backward compatible)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] is None
    assert output["field"] == "parent_objective"


# ============================================================================
# Error Cases
# ============================================================================


def test_get_objective_metadata_issue_not_found() -> None:
    """Test error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["9999", "parent_objective"],
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
    body = make_objective_header_body(parent_objective=300)
    fake_gh = FakeGitHubIssues(issues={789: make_issue_info(789, body)})
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["789", "parent_objective"],
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
    assert output["issue_number"] == 789
    assert output["field"] == "parent_objective"
    assert output["value"] == 300


def test_json_output_structure_error() -> None:
    """Test JSON output structure on error."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_objective_metadata,
        ["999", "parent_objective"],
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
