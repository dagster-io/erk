"""Tests for erk plan extraction complete command.

Layer 4 (Business Logic Tests): Tests extraction complete command using fakes.
"""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata import format_plan_header_body

from erk.cli.cli import cli
from erk.cli.constants import DOCS_EXTRACTED_LABEL, ERK_EXTRACTION_LABEL, ERK_PLAN_LABEL
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_extraction_issue(
    number: int,
    source_plan_issues: list[int],
    extraction_session_ids: list[str],
) -> IssueInfo:
    """Create an extraction plan IssueInfo for testing."""
    body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
        plan_type="extraction",
        source_plan_issues=source_plan_issues,
        extraction_session_ids=extraction_session_ids,
    )
    return IssueInfo(
        number=number,
        title=f"Extraction Plan #{number} [erk-extraction]",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=[ERK_PLAN_LABEL, ERK_EXTRACTION_LABEL],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-user",
    )


def _make_source_issue(number: int, title: str) -> IssueInfo:
    """Create a source plan IssueInfo for testing."""
    return IssueInfo(
        number=number,
        title=title,
        body="Source plan body",
        state="CLOSED",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-user",
    )


def test_complete_marks_source_plans() -> None:
    """Test complete adds docs-extracted label to all source plans."""
    # Arrange
    extraction_issue = _make_extraction_issue(
        number=100,
        source_plan_issues=[42, 43],
        extraction_session_ids=["session-abc"],
    )
    issues = FakeGitHubIssues(
        issues={
            100: extraction_issue,
            42: _make_source_issue(42, "Source Plan 1"),
            43: _make_source_issue(43, "Source Plan 2"),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "100"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Marked plan #42 as docs-extracted" in result.output
        assert "Marked plan #43 as docs-extracted" in result.output
        assert "marked 2 source plan(s)" in result.output

        # Verify labels were added
        source_42 = issues.get_issue(env.cwd, 42)
        source_43 = issues.get_issue(env.cwd, 43)
        assert DOCS_EXTRACTED_LABEL in source_42.labels
        assert DOCS_EXTRACTED_LABEL in source_43.labels


def test_complete_creates_label_if_missing() -> None:
    """Test complete creates docs-extracted label in repo if needed."""
    # Arrange
    extraction_issue = _make_extraction_issue(
        number=100,
        source_plan_issues=[42],
        extraction_session_ids=["session-abc"],
    )
    issues = FakeGitHubIssues(
        issues={
            100: extraction_issue,
            42: _make_source_issue(42, "Source Plan"),
        },
        labels=set(),  # No labels in repo
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "100"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert DOCS_EXTRACTED_LABEL in issues.labels


def test_complete_idempotent() -> None:
    """Test complete can be run multiple times safely."""
    # Arrange - source plan already has the label
    extraction_issue = _make_extraction_issue(
        number=100,
        source_plan_issues=[42],
        extraction_session_ids=["session-abc"],
    )
    source_issue = _make_source_issue(42, "Source Plan")
    # Add the label to source issue
    source_issue = IssueInfo(
        number=source_issue.number,
        title=source_issue.title,
        body=source_issue.body,
        state=source_issue.state,
        url=source_issue.url,
        labels=[ERK_PLAN_LABEL, DOCS_EXTRACTED_LABEL],
        assignees=[],
        created_at=source_issue.created_at,
        updated_at=source_issue.updated_at,
        author="test-user",
    )
    issues = FakeGitHubIssues(
        issues={
            100: extraction_issue,
            42: source_issue,
        },
        labels={DOCS_EXTRACTED_LABEL},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "100"], obj=ctx)

        # Assert
        assert result.exit_code == 0


def test_complete_rejects_non_extraction_plan() -> None:
    """Test complete fails for non-extraction plan types."""
    # Arrange - standard plan (no plan_type or plan_type: standard)
    standard_body = format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="user123",
    )
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

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "100"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "not an extraction plan" in result.output


def test_complete_rejects_issue_without_plan_header() -> None:
    """Test complete fails for issue without plan-header block."""
    # Arrange - issue without plan-header metadata
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

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "100"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "plan-header" in result.output


def test_complete_handles_missing_source_issue() -> None:
    """Test complete continues when a source issue is missing."""
    # Arrange - extraction references issue 42, but 42 doesn't exist
    extraction_issue = _make_extraction_issue(
        number=100,
        source_plan_issues=[42, 43],  # 42 doesn't exist
        extraction_session_ids=["session-abc"],
    )
    issues = FakeGitHubIssues(
        issues={
            100: extraction_issue,
            43: _make_source_issue(43, "Source Plan 2"),
            # Issue 42 is missing
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "100"], obj=ctx)

        # Assert - should partially complete with warning
        assert result.exit_code == 0
        assert "Warning" in result.output or "partially completed" in result.output
        # Issue 43 should still be marked
        source_43 = issues.get_issue(env.cwd, 43)
        assert DOCS_EXTRACTED_LABEL in source_43.labels


def test_complete_with_invalid_identifier() -> None:
    """Test complete with invalid identifier shows helpful error."""
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "extraction", "complete", "not-a-number"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Invalid issue number or URL" in result.output


def test_complete_with_github_url() -> None:
    """Test complete accepts GitHub URL as identifier."""
    # Arrange
    extraction_issue = _make_extraction_issue(
        number=100,
        source_plan_issues=[42],
        extraction_session_ids=["session-abc"],
    )
    issues = FakeGitHubIssues(
        issues={
            100: extraction_issue,
            42: _make_source_issue(42, "Source Plan"),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(
            cli,
            [
                "plan",
                "extraction",
                "complete",
                "https://github.com/owner/repo/issues/100",
            ],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Marked plan #42 as docs-extracted" in result.output
