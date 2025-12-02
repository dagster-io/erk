"""Tests for top-level plan commands (dash, get, close, retry)."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.cli import cli
from erk.cli.commands.plan.list_cmd import _run_interactive_mode
from erk.tui.context import ErkDashContext
from erk.tui.runner import FakeTuiRunner
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
    )


def test_run_interactive_mode_creates_app_without_hanging() -> None:
    """Test that _run_interactive_mode creates app via FakeTuiRunner without hanging.

    Uses FakeTuiRunner to capture the app without starting Textual event loop.
    This tests the CLI-to-app wiring without any mock.patch.
    """
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

        # Create FakeTuiRunner to capture app without running event loop
        tui_runner = FakeTuiRunner()
        dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)

        # Act - Call _run_interactive_mode directly with injected dash_ctx
        _run_interactive_mode(
            ctx=ctx,
            label=(),
            state=None,
            run_state=None,
            runs=True,
            prs=True,
            limit=None,
            interval=15.0,
            dash_ctx=dash_ctx,
        )

        # Assert - App was created and passed to runner without hanging
        assert len(tui_runner.apps_run) == 1
        app = tui_runner.apps_run[0]
        assert app is not None


def test_run_interactive_mode_passes_state_filter() -> None:
    """Test that state filter is correctly passed to app."""
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

        tui_runner = FakeTuiRunner()
        dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)

        # Act - Call with state="open"
        _run_interactive_mode(
            ctx=ctx,
            label=(),
            state="open",
            run_state=None,
            runs=True,
            prs=True,
            limit=None,
            interval=15.0,
            dash_ctx=dash_ctx,
        )

        # Assert - State filter was passed to app
        assert len(tui_runner.apps_run) == 1
        app = tui_runner.apps_run[0]
        assert app._plan_filters.state == "open"


def test_run_interactive_mode_passes_label_filter() -> None:
    """Test that label filter is correctly passed to app."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "bug"],
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

        tui_runner = FakeTuiRunner()
        dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)

        # Act - Call with custom labels
        _run_interactive_mode(
            ctx=ctx,
            label=("erk-plan", "bug"),
            state=None,
            run_state=None,
            runs=True,
            prs=True,
            limit=None,
            interval=15.0,
            dash_ctx=dash_ctx,
        )

        # Assert - Labels were passed to app
        assert len(tui_runner.apps_run) == 1
        app = tui_runner.apps_run[0]
        assert app._plan_filters.labels == ("erk-plan", "bug")


def test_run_interactive_mode_passes_refresh_interval() -> None:
    """Test that refresh interval is correctly passed to app."""
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

        tui_runner = FakeTuiRunner()
        dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)

        # Act - Call with custom interval
        _run_interactive_mode(
            ctx=ctx,
            label=(),
            state=None,
            run_state=None,
            runs=True,
            prs=True,
            limit=None,
            interval=30.0,
            dash_ctx=dash_ctx,
        )

        # Assert - Interval was passed to app
        assert len(tui_runner.apps_run) == 1
        app = tui_runner.apps_run[0]
        assert app._refresh_interval == 30.0


def test_run_interactive_mode_injects_dash_ctx_into_app() -> None:
    """Test that dash_ctx is injected into the app for browser launching."""
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

        tui_runner = FakeTuiRunner()
        dash_ctx = ErkDashContext.for_test(ctx, tui_runner=tui_runner)

        # Act
        _run_interactive_mode(
            ctx=ctx,
            label=(),
            state=None,
            run_state=None,
            runs=True,
            prs=True,
            limit=None,
            interval=15.0,
            dash_ctx=dash_ctx,
        )

        # Assert - dash_ctx was passed to app
        assert len(tui_runner.apps_run) == 1
        app = tui_runner.apps_run[0]
        assert app._dash_ctx is dash_ctx


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
