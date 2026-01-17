"""Tests for top-level plan commands (dash, get, close, retry)."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.plan.list_cmd import dash
from erk_shared.github.issues import FakeGitHubIssues
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    make_test_plan,
    plan_to_issue,
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
    plan1 = make_test_plan(1, title="Test Plan")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
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
    open_plan = make_test_plan(1, title="Open Plan")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(open_plan)})
        github = FakeGitHub(issues_data=[plan_to_issue(open_plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Mock _run_interactive_mode to verify filters are passed
        with patch("erk.cli.commands.plan.list_cmd._run_interactive_mode") as mock_run:
            # Act - Filter for open plans using dash command
            result = runner.invoke(dash, ["--state", "open"], obj=ctx)

            # Assert - Should pass state filter to interactive mode
            assert result.exit_code == 0
            assert mock_run.called
            # Verify state filter was passed as keyword argument
            call_args = mock_run.call_args
            assert call_args.kwargs["state"] == "open"


def test_top_level_view_command_works() -> None:
    """Test that 'erk plan view' command works."""
    # Arrange
    issue1 = make_test_plan(
        123,
        title="Test Issue",
        body="Issue body content",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"123": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use plan view command
        result = runner.invoke(cli, ["plan", "view", "123"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # ID is now rendered as clickable link with OSC 8 escape sequences
        assert "#123" in result.output
        assert "Test Issue" in result.output


def test_top_level_close_command_works() -> None:
    """Test that 'erk plan close' command works."""
    # Arrange
    issue1 = make_test_plan(
        456,
        title="Plan to Close",
        body="content",  # GitHubPlanStore requires non-empty body
        metadata={"number": 456},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, fake_issues = create_plan_store_with_plans({"456": issue1})
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act - Use plan close command
        result = runner.invoke(cli, ["plan", "close", "456"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert 456 in fake_issues.closed_issues
