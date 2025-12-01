"""Tests for plan close command."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_close_plan_with_issue_number() -> None:
    """Test closing a plan with issue number."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert "42" in store.closed_plans
        # Verify plan state was updated to closed
        closed_plan = store.get_plan(env.erk_root, "42")
        assert closed_plan.state == PlanState.CLOSED


def test_close_plan_not_found() -> None:
    """Test closing a plan that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "close", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "not found" in result.output or "999" in result.output
