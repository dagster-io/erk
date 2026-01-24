"""Tests for erk plan learn complete command.

Layer 4 (Business Logic Tests): Tests learn complete command using fakes.

NOTE: The complete command is deprecated because source_plan_issues
metadata field has been removed from the schema.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.constants import ERK_LEARN_LABEL, ERK_PLAN_LABEL
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_learn_issue(number: int) -> IssueInfo:
    """Create a learn plan IssueInfo for testing.

    Learn plans are identified by the erk-learn label.
    """
    body = format_plan_header_body_for_test(created_by="user123")
    return IssueInfo(
        number=number,
        title=f"[erk-learn] Learn Plan #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=[ERK_PLAN_LABEL, ERK_LEARN_LABEL],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-user",
    )


def test_complete_is_deprecated() -> None:
    """Test that complete command shows deprecation error."""
    learn_issue = _make_learn_issue(number=100)
    issues = FakeGitHubIssues(issues={100: learn_issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["plan", "learn", "complete", "100"], obj=ctx)

        # Command should fail with deprecation message
        assert result.exit_code != 0
        assert "deprecated" in result.output.lower()


def test_complete_rejects_non_learn_plan() -> None:
    """Test complete fails for non-learn plan types."""
    # Standard plan (without erk-learn label)
    standard_body = format_plan_header_body_for_test(created_by="user123")
    standard_issue = IssueInfo(
        number=100,
        title="Standard Plan [erk-plan]",
        body=standard_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/100",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-user",
    )
    issues = FakeGitHubIssues(issues={100: standard_issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["plan", "learn", "complete", "100"], obj=ctx)

        # Should fail because it's not a learn plan
        assert result.exit_code != 0
        assert "not a learn plan" in result.output


def test_complete_rejects_issue_without_plan_header() -> None:
    """Test complete fails for issue without plan-header block."""
    plain_issue = IssueInfo(
        number=100,
        title="Plain Issue",
        body="This is just a plain issue body",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/100",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-user",
    )
    issues = FakeGitHubIssues(issues={100: plain_issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["plan", "learn", "complete", "100"], obj=ctx)

        assert result.exit_code != 0
        assert "plan-header" in result.output


def test_complete_with_invalid_identifier() -> None:
    """Test complete with invalid identifier shows helpful error."""
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["plan", "learn", "complete", "not-a-number"], obj=ctx)

        assert result.exit_code != 0
        assert "Invalid issue number or URL" in result.output
