"""Tests for plan list command."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from erk.cli.cli import cli
from erk.core.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup.

    Used to adapt tests from FakePlanStore to FakeGitHubIssues.
    """
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def test_list_plans_basic() -> None:
    """Test basic plan listing with no filters."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Test Plan One",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    plan2 = Plan(
        plan_identifier="2",
        title="Test Plan Two",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#1" in result.output
        assert "Test Plan One" in result.output
        assert "#2" in result.output
        assert "Test Plan Two" in result.output
        assert "🟢 open" in result.output


def test_list_plans_empty() -> None:
    """Test listing when no plans exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found." in result.output


def test_list_plans_shows_open_plans_only() -> None:
    """Test that list command shows only open plans by default."""
    # Arrange
    open_plan = Plan(
        plan_identifier="1",
        title="Open Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_plan = Plan(
        plan_identifier="2",
        title="Closed Plan",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Open Plan" in result.output
        assert "#2" not in result.output
        assert "Closed Plan" not in result.output


def test_list_plans_shows_state_column() -> None:
    """Test that state column displays correctly with emojis."""
    # Arrange
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={42: plan_to_issue(plan)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#42" in result.output
        assert "Test Plan" in result.output
        assert "🟢 open" in result.output


def test_list_plans_truncates_long_titles() -> None:
    """Test that titles longer than 50 characters are truncated."""
    # Arrange
    long_title = (
        "This is a very long title that should be truncated because it exceeds fifty characters"
    )
    plan = Plan(
        plan_identifier="99",
        title=long_title,
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/99",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={99: plan_to_issue(plan)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#99" in result.output
        # Title should be truncated to 47 chars + "..."
        assert "..." in result.output
        # Full title should not appear
        assert long_title not in result.output


def test_list_plans_shows_clickable_links() -> None:
    """Test that plan numbers are clickable links."""
    # Arrange
    plan = Plan(
        plan_identifier="123",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/123",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={123: plan_to_issue(plan)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#123" in result.output
        assert "Test Plan" in result.output
