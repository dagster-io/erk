"""Tests for top-level plan commands (dash, get, close, retry)."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.cli import cli
from erk.cli.commands.plan.list_cmd import dash
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url or "",
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        author="test-user",
    )


def test_top_level_dash_command_works() -> None:
    """Test that top-level 'erk dash' command routes correctly.

    Note: This test mocks _run_interactive_mode because Textual TUI apps
    don't work properly with Click's CliRunner and can leave threads running,
    causing pytest-xdist workers to hang.
    """
    from unittest.mock import patch

    runner = CliRunner()

    # Mock _run_interactive_mode to verify CLI routing works without
    # actually running the Textual TUI (which hangs in test environments)
    with patch("erk.cli.commands.plan.list_cmd._run_interactive_mode") as mock_run:
        result = runner.invoke(cli, ["dash"])

        # Assert - command routes correctly and calls _run_interactive_mode
        assert result.exit_code == 0
        assert mock_run.called


def test_dash_command_routes_to_interactive_mode() -> None:
    """Test that 'erk dash' command routes to interactive mode.

    Note: This test mocks _run_interactive_mode because Textual TUI apps
    don't work properly with Click's CliRunner and can leave threads running,
    causing pytest-xdist workers to hang.
    """
    from unittest.mock import patch

    from erk_shared.github.fake import FakeGitHub

    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1)})
        github = FakeGitHub(issues=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Mock _run_interactive_mode to verify CLI routing works
        with patch("erk.cli.commands.plan.list_cmd._run_interactive_mode") as mock_run:
            # Act - Use dash command directly
            result = runner.invoke(dash, [], obj=ctx)

            # Assert - Should route to interactive mode
            assert result.exit_code == 0
            assert mock_run.called


def test_dash_command_passes_filters_to_interactive_mode() -> None:
    """Test that plan filters are passed to interactive mode.

    Note: This test mocks _run_interactive_mode because Textual TUI apps
    don't work properly with Click's CliRunner and can leave threads running,
    causing pytest-xdist workers to hang.
    """
    from unittest.mock import patch

    from erk_shared.github.fake import FakeGitHub

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

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(open_plan)})
        github = FakeGitHub(issues=[plan_to_issue(open_plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Mock _run_interactive_mode to verify filters are passed
        with patch("erk.cli.commands.plan.list_cmd._run_interactive_mode") as mock_run:
            # Act - Filter for open plans using dash command
            result = runner.invoke(dash, ["--state", "open"], obj=ctx)

            # Assert - Should pass state filter to interactive mode
            assert result.exit_code == 0
            assert mock_run.called
            # Verify state filter was passed (second positional arg after ctx)
            call_args = mock_run.call_args
            assert call_args[0][2] == "open"  # state argument


def test_top_level_get_command_works() -> None:
    """Test that 'erk plan get' command works."""
    # Arrange
    issue1 = Plan(
        plan_identifier="123",
        title="Test Issue",
        body="Issue body content",
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
        store = FakePlanStore(plans={"123": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use plan get command
        result = runner.invoke(cli, ["plan", "get", "123"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # ID is now rendered as clickable link with OSC 8 escape sequences
        assert "#123" in result.output
        assert "Test Issue" in result.output


def test_top_level_close_command_works() -> None:
    """Test that 'erk plan close' command works."""
    # Arrange
    issue1 = Plan(
        plan_identifier="456",
        title="Plan to Close",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/456",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 456},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"456": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use plan close command
        result = runner.invoke(cli, ["plan", "close", "456"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert store.closed_plans == ["456"]
