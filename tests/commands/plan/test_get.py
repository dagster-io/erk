"""Tests for plan-issue get command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_get_plan_displays_issue() -> None:
    """Test fetching and displaying a plan issue."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue description",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "get", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Test Issue" in result.output
        assert "OPEN" in result.output
        assert "42" in result.output
        assert "erk-plan" in result.output
        assert "bug" in result.output
        assert "alice" in result.output
        assert "This is a test issue description" in result.output


def test_get_plan_not_found() -> None:
    """Test fetching a plan issue that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "get", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "not found" in result.output or "999" in result.output


def test_get_plan_minimal_fields() -> None:
    """Test displaying issue with minimal fields (no labels, assignees, body)."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="1",
        title="Minimal Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"1": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "get", "1"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Minimal Issue" in result.output
        assert "CLOSED" in result.output


def test_get_plan_string_identifier() -> None:
    """Test get with non-numeric string identifier (e.g., Jira style)."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="PROJ-123",
        title="Jira-style Issue",
        body="",
        state=PlanState.OPEN,
        url="https://jira.example.com/browse/PROJ-123",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"PROJ-123": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "get", "PROJ-123"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Jira-style Issue" in result.output
        assert "PROJ-123" in result.output
