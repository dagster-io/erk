"""Unit tests for update-plan-header exec command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_plan_header import update_plan_header
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_issue(number: int, body: str) -> IssueInfo:
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


def _make_issue_with_plan_header(number: int) -> IssueInfo:
    """Create a test issue with a plan-header metadata block."""
    body = format_plan_header_body_for_test(
        created_at="2025-01-01T00:00:00Z",
        created_by="testuser",
    )
    return _make_issue(number, body)


# ============================================================================
# Success Cases
# ============================================================================


def test_update_single_field() -> None:
    """update-plan-header sets a single field in plan-header."""
    issue = _make_issue_with_plan_header(123)
    fake_gh = FakeGitHubIssues(issues={123: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["123", "objective_issue=7823"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == "123"
    assert output["fields_updated"] == ["objective_issue"]

    # Verify metadata was actually updated
    updated_issue = fake_gh.get_issue(repo_root, 123)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["objective_issue"] == 7823


def test_update_multiple_fields() -> None:
    """update-plan-header sets multiple fields at once."""
    issue = _make_issue_with_plan_header(456)
    fake_gh = FakeGitHubIssues(issues={456: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["456", "lifecycle_stage=implementing", "objective_issue=7823"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert set(output["fields_updated"]) == {"lifecycle_stage", "objective_issue"}

    updated_issue = fake_gh.get_issue(repo_root, 456)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["lifecycle_stage"] == "implementing"
    assert block.data["objective_issue"] == 7823


def test_overwrites_existing() -> None:
    """update-plan-header overwrites existing field values."""
    body = format_plan_header_body_for_test(
        created_at="2025-01-01T00:00:00Z",
        created_by="testuser",
        objective_issue=999,
    )
    issue = _make_issue(789, body)
    fake_gh = FakeGitHubIssues(issues={789: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["789", "objective_issue=7823"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    updated_issue = fake_gh.get_issue(repo_root, 789)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["objective_issue"] == 7823


# ============================================================================
# Type Coercion
# ============================================================================


def test_null_coercion() -> None:
    """update-plan-header coerces 'null' string to None."""
    body = format_plan_header_body_for_test(
        created_at="2025-01-01T00:00:00Z",
        created_by="testuser",
        objective_issue=7823,
    )
    issue = _make_issue(100, body)
    fake_gh = FakeGitHubIssues(issues={100: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["100", "objective_issue=null"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    updated_issue = fake_gh.get_issue(repo_root, 100)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data.get("objective_issue") is None


def test_int_coercion() -> None:
    """update-plan-header coerces valid integer strings to int."""
    issue = _make_issue_with_plan_header(101)
    fake_gh = FakeGitHubIssues(issues={101: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["101", "objective_issue=7823"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    updated_issue = fake_gh.get_issue(repo_root, 101)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["objective_issue"] == 7823
    assert isinstance(block.data["objective_issue"], int)


def test_string_preserved() -> None:
    """update-plan-header preserves string values as strings."""
    issue = _make_issue_with_plan_header(102)
    fake_gh = FakeGitHubIssues(issues={102: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["102", "branch_name=my-branch"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    updated_issue = fake_gh.get_issue(repo_root, 102)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["branch_name"] == "my-branch"
    assert isinstance(block.data["branch_name"], str)


# ============================================================================
# Schema Validation Errors
# ============================================================================


def test_schema_validation_rejects_unknown_field() -> None:
    """update-plan-header rejects unknown field names via schema validation."""
    issue = _make_issue_with_plan_header(200)
    fake_gh = FakeGitHubIssues(issues={200: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["200", "bogus_field=x"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_schema_validation_rejects_invalid_lifecycle_stage() -> None:
    """update-plan-header rejects invalid lifecycle_stage values."""
    issue = _make_issue_with_plan_header(201)
    fake_gh = FakeGitHubIssues(issues={201: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["201", "lifecycle_stage=bogus"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_immutable_field_protected() -> None:
    """update-plan-header silently ignores immutable fields (backend behavior)."""
    issue = _make_issue_with_plan_header(202)
    fake_gh = FakeGitHubIssues(issues={202: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["202", "created_by=hacker"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    # Backend silently ignores immutable fields, so command succeeds
    assert result.exit_code == 0

    updated_issue = fake_gh.get_issue(repo_root, 202)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    # Value should be preserved, not overwritten
    assert block.data["created_by"] == "testuser"


# ============================================================================
# Input Validation Errors
# ============================================================================


def test_no_fields_provided() -> None:
    """update-plan-header exits 1 when no fields are provided."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_plan_header,
        ["300"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_fields"


def test_invalid_field_format() -> None:
    """update-plan-header exits 1 for fields without '=' separator."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_plan_header,
        ["301", "no-equals-sign"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_field_format"


# ============================================================================
# Plan Not Found / No Header Block
# ============================================================================


def test_plan_not_found() -> None:
    """update-plan-header exits 1 when plan doesn't exist."""
    fake_gh = FakeGitHubIssues()
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["999", "lifecycle_stage=planned"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_no_plan_header_block() -> None:
    """update-plan-header exits 1 when issue has no plan-header block."""
    old_format_body = """# Old Format Issue

This is an issue created before plan-header blocks were introduced.
"""
    issue = _make_issue(400, old_format_body)
    fake_gh = FakeGitHubIssues(issues={400: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_plan_header,
        ["400", "lifecycle_stage=planned"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
