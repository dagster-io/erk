"""Tests for plan docs commands."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.constants import DOCS_EXTRACTED_LABEL, ERK_PLAN_LABEL
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_issue(
    number: int,
    title: str,
    *,
    state: str = "CLOSED",
    labels: list[str] | None = None,
) -> IssueInfo:
    """Create an IssueInfo for testing."""
    return IssueInfo(
        number=number,
        title=title,
        body="Test issue body",
        state=state,
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=labels if labels is not None else [ERK_PLAN_LABEL],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        author="test-user",
    )


def test_unextracted_shows_closed_plans_without_label() -> None:
    """Test unextracted lists only closed plans missing docs-extracted label."""
    # Arrange
    issues = FakeGitHubIssues(
        issues={
            1: _make_issue(1, "Plan 1 - closed, no label"),
            2: _make_issue(2, "Plan 2 - closed, no label"),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextracted"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 unextracted plan(s)" in result.output
        assert "#1" in result.output
        assert "#2" in result.output


def test_unextracted_excludes_plans_with_label() -> None:
    """Test unextracted filters out plans with docs-extracted label."""
    # Arrange
    issues = FakeGitHubIssues(
        issues={
            1: _make_issue(1, "Plan 1 - closed, no label"),
            2: _make_issue(
                2,
                "Plan 2 - closed, has label",
                labels=[ERK_PLAN_LABEL, DOCS_EXTRACTED_LABEL],
            ),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextracted"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 unextracted plan(s)" in result.output
        assert "#1" in result.output
        assert "#2" not in result.output


def test_unextracted_excludes_open_plans() -> None:
    """Test unextracted only shows closed plans."""
    # Arrange - FakeGitHubIssues filters by state in list_issues
    issues = FakeGitHubIssues(
        issues={
            1: _make_issue(1, "Plan 1 - open", state="OPEN"),
            2: _make_issue(2, "Plan 2 - closed", state="CLOSED"),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextracted"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 unextracted plan(s)" in result.output
        assert "#1" not in result.output  # Open plan excluded
        assert "#2" in result.output  # Closed plan included


def test_unextracted_empty_result() -> None:
    """Test unextracted shows message when no unextracted plans exist."""
    # Arrange - all closed plans have the label
    issues = FakeGitHubIssues(
        issues={
            1: _make_issue(
                1,
                "Plan 1 - extracted",
                labels=[ERK_PLAN_LABEL, DOCS_EXTRACTED_LABEL],
            ),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextracted"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No unextracted plans found" in result.output


def test_extract_adds_label() -> None:
    """Test extract adds docs-extracted label to issue."""
    # Arrange
    issues = FakeGitHubIssues(
        issues={
            42: _make_issue(42, "Test Plan"),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "extract", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Marked plan #42 as docs-extracted" in result.output
        # Verify label was added
        updated_issue = issues.get_issue(env.cwd, 42)
        assert DOCS_EXTRACTED_LABEL in updated_issue.labels


def test_extract_creates_label_if_missing() -> None:
    """Test extract creates label in repo if it doesn't exist."""
    # Arrange - no labels in repo yet
    issues = FakeGitHubIssues(
        issues={
            42: _make_issue(42, "Test Plan"),
        },
        labels=set(),  # No labels in repo
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "extract", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Marked plan #42 as docs-extracted" in result.output
        # Verify label was created in repo
        assert DOCS_EXTRACTED_LABEL in issues.labels
        # Verify label creation was tracked
        assert len(issues.created_labels) == 1
        assert issues.created_labels[0][0] == DOCS_EXTRACTED_LABEL


def test_extract_idempotent() -> None:
    """Test extract can be run twice without error."""
    # Arrange - issue already has the label
    issues = FakeGitHubIssues(
        issues={
            42: _make_issue(
                42,
                "Test Plan",
                labels=[ERK_PLAN_LABEL, DOCS_EXTRACTED_LABEL],
            ),
        },
        labels={DOCS_EXTRACTED_LABEL},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "extract", "42"], obj=ctx)

        # Assert - should succeed without error
        assert result.exit_code == 0
        assert "Marked plan #42 as docs-extracted" in result.output


def test_extract_invalid_identifier() -> None:
    """Test extract with invalid identifier shows helpful error."""
    # Arrange
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "extract", "not-a-number"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Invalid issue number or URL" in result.output
        assert "not-a-number" in result.output


def test_extract_with_github_url() -> None:
    """Test extract accepts GitHub URL as identifier."""
    # Arrange
    issues = FakeGitHubIssues(
        issues={
            42: _make_issue(42, "Test Plan"),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(
            cli,
            ["plan", "docs", "extract", "https://github.com/owner/repo/issues/42"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Marked plan #42 as docs-extracted" in result.output


def test_unextract_removes_label() -> None:
    """Test unextract removes docs-extracted label from issue."""
    # Arrange - issue has the label
    issues = FakeGitHubIssues(
        issues={
            42: _make_issue(
                42,
                "Test Plan",
                labels=[ERK_PLAN_LABEL, DOCS_EXTRACTED_LABEL],
            ),
        }
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextract", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Removed docs-extracted label from plan #42" in result.output
        # Verify label was removed
        updated_issue = issues.get_issue(env.cwd, 42)
        assert DOCS_EXTRACTED_LABEL not in updated_issue.labels
        assert ERK_PLAN_LABEL in updated_issue.labels  # Other labels preserved


def test_unextract_invalid_identifier() -> None:
    """Test unextract with invalid identifier shows helpful error."""
    # Arrange
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextract", "not-a-number"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Invalid issue number or URL" in result.output
        assert "not-a-number" in result.output


def test_unextract_issue_not_found() -> None:
    """Test unextract with nonexistent issue shows error."""
    # Arrange
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "unextract", "999"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Error" in result.output


def test_extract_issue_not_found() -> None:
    """Test extract with nonexistent issue shows error."""
    # Arrange
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "docs", "extract", "999"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Error" in result.output
