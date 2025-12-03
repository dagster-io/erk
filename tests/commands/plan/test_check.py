"""Tests for plan check command."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata import MetadataBlock, render_metadata_block

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_check_valid_plan_passes() -> None:
    """Test validating a valid Schema v2 plan."""
    # Arrange
    # Valid plan-header metadata
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "alice",
        "worktree_name": "test-feature",
    }
    plan_header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))

    # Valid plan-body in first comment
    plan_content = """# Plan: Test Feature

## Steps
1. Step one
2. Step two"""
    plan_body_block = render_metadata_block(MetadataBlock("plan-body", {"content": plan_content}))

    issue = IssueInfo(
        number=42,
        title="Test Feature",
        body=plan_header_block,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={42: issue},
            comments={42: [plan_body_block]},
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Validating plan #42" in result.output
        assert "[PASS] plan-header metadata block present" in result.output
        assert "[PASS] plan-header has required fields" in result.output
        assert "[PASS] First comment exists" in result.output
        assert "[PASS] plan-body content extractable" in result.output
        assert "Plan validation passed" in result.output


def test_check_missing_plan_header_fails() -> None:
    """Test validating a plan without plan-header block."""
    # Arrange
    issue = IssueInfo(
        number=42,
        title="Test Feature",
        body="No metadata block here",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={42: issue},
            comments={42: []},
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[FAIL] plan-header metadata block present" in result.output
        assert "Plan validation failed" in result.output


def test_check_missing_required_field_fails() -> None:
    """Test validating a plan with invalid plan-header (missing required field)."""
    # Arrange
    # Missing created_by field (worktree_name is optional, so test with a truly required field)
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        # created_by is missing
    }
    plan_header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))

    issue = IssueInfo(
        number=42,
        title="Test Feature",
        body=plan_header_block,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={42: issue},
            comments={42: []},
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[PASS] plan-header metadata block present" in result.output
        assert "[FAIL]" in result.output
        assert "created_by" in result.output
        assert "Plan validation failed" in result.output


def test_check_missing_first_comment_fails() -> None:
    """Test validating a plan without any comments."""
    # Arrange
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "alice",
        "worktree_name": "test-feature",
    }
    plan_header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))

    issue = IssueInfo(
        number=42,
        title="Test Feature",
        body=plan_header_block,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={42: issue},
            comments={42: []},
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[FAIL] First comment exists" in result.output
        assert "Plan validation failed" in result.output


def test_check_missing_plan_body_fails() -> None:
    """Test validating a plan without plan-body in first comment."""
    # Arrange
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "alice",
        "worktree_name": "test-feature",
    }
    plan_header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))

    issue = IssueInfo(
        number=42,
        title="Test Feature",
        body=plan_header_block,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # First comment without plan-body block
        issues = FakeGitHubIssues(
            issues={42: issue},
            comments={42: ["Just a regular comment"]},
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[PASS] First comment exists" in result.output
        assert "[FAIL] plan-body content extractable" in result.output
        assert "Plan validation failed" in result.output


def test_check_github_url_parsing() -> None:
    """Test check command with GitHub URL instead of issue number."""
    # Arrange
    plan_header_data = {
        "schema_version": "2",
        "created_at": "2024-01-01T00:00:00Z",
        "created_by": "alice",
        "worktree_name": "test-feature",
    }
    plan_header_block = render_metadata_block(MetadataBlock("plan-header", plan_header_data))

    plan_content = """# Plan: Test Feature

## Steps
1. Step one"""
    plan_body_block = render_metadata_block(MetadataBlock("plan-body", {"content": plan_content}))

    issue = IssueInfo(
        number=42,
        title="Test Feature",
        body=plan_header_block,
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={42: issue},
            comments={42: [plan_body_block]},
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Use GitHub URL instead of number
        result = runner.invoke(
            cli,
            ["plan", "check", "https://github.com/owner/repo/issues/42"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Validating plan #42" in result.output
        assert "Plan validation passed" in result.output


def test_check_invalid_identifier_fails() -> None:
    """Test check command with invalid identifier format."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={}, comments={})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "check", "not-a-valid-identifier"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Invalid issue number or URL" in result.output
