"""Tests for plan check command."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_plan(
    plan_identifier: str,
    title: str = "Test Feature",
    body: str = "# Plan Content\n\n## Steps\n1. Step one",
    labels: list[str] | None = None,
) -> Plan:
    """Create a Plan for testing."""
    return Plan(
        plan_identifier=plan_identifier,
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{plan_identifier}",
        labels=labels if labels is not None else ["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": int(plan_identifier)},
    )


def test_check_valid_plan_passes() -> None:
    """Test validating a valid plan with content and erk-plan label."""
    # Arrange
    plan = _make_plan("42")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Validating plan #42" in result.output
        assert "[PASS] Plan can be retrieved" in result.output
        assert "[PASS] Plan has erk-plan label" in result.output
        assert "[PASS] Plan has content" in result.output
        assert "Plan validation passed" in result.output


def test_check_missing_label_fails() -> None:
    """Test validating a plan without erk-plan label."""
    # Arrange
    plan = _make_plan("42", labels=["other-label"])

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[PASS] Plan can be retrieved" in result.output
        assert "[FAIL] Plan has erk-plan label" in result.output
        assert "Plan validation failed" in result.output


def test_check_empty_body_fails() -> None:
    """Test validating a plan with empty body content."""
    # Arrange
    plan = _make_plan("42", body="")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[PASS] Plan can be retrieved" in result.output
        assert "[PASS] Plan has erk-plan label" in result.output
        assert "[FAIL] Plan has content" in result.output
        assert "Plan validation failed" in result.output


def test_check_whitespace_only_body_fails() -> None:
    """Test validating a plan with whitespace-only body."""
    # Arrange
    plan = _make_plan("42", body="   \n  \t  ")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "check", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "[FAIL] Plan has content" in result.output


def test_check_github_url_parsing() -> None:
    """Test check command with GitHub URL instead of issue number."""
    # Arrange
    plan = _make_plan("42")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        ctx = build_workspace_test_context(env, plan_store=plan_store)

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
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "check", "not-a-valid-identifier"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Invalid identifier" in result.output


def test_check_nonexistent_plan_fails() -> None:
    """Test check command with plan that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore()
        ctx = build_workspace_test_context(env, plan_store=plan_store)

        # Act
        result = runner.invoke(cli, ["plan", "check", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Failed to fetch plan" in result.output
