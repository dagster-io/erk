"""Tests for plan list filtering functionality.

Tests state, labels, limit, and combined filters for plan list command.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.github_issues import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import (
    build_fake_plan_list_service,
    build_workspace_test_context,
)
from tests.test_utils.env_helpers import erk_inmem_env


def test_plan_list_no_filters() -> None:
    """Test listing all plan issues with no filters (defaults to open plans only)."""
    # Arrange - Create two OPEN plans (no filter defaults to open state)
    plan1 = Plan(
        plan_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    plan2 = Plan(
        plan_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.OPEN,  # Changed to OPEN to match default behavior
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],  # Must have erk-plan label to be returned by default
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])
        plan_service = build_fake_plan_list_service([plan1, plan2])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["pr", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#1" in result.output
        assert "#2" in result.output


def test_plan_list_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    # Arrange
    open_plan = Plan(
        plan_identifier="1",
        title="Open Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    closed_plan = Plan(
        plan_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        github = FakeLocalGitHub(issues_data=[plan_to_issue(open_plan), plan_to_issue(closed_plan)])
        plan_service = build_fake_plan_list_service([open_plan, closed_plan])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Act - Filter for open issues
        result = runner.invoke(cli, ["pr", "list", "--state", "open"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "#2" not in result.output


def test_plan_list_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    # Arrange
    plan_with_both = Plan(
        plan_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    plan_with_one = Plan(
        plan_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(plan_with_both), 2: plan_to_issue(plan_with_one)}
        )
        github = FakeLocalGitHub(
            issues_data=[plan_to_issue(plan_with_both), plan_to_issue(plan_with_one)]
        )
        plan_service = build_fake_plan_list_service([plan_with_both, plan_with_one])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Act - Filter for both labels (AND logic)
        result = runner.invoke(
            cli,
            ["pr", "list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "#2" not in result.output


def test_plan_list_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    # Arrange
    plans_dict: dict[int, IssueInfo] = {}
    issues_list: list[IssueInfo] = []
    all_plans: list[Plan] = []
    for i in range(1, 6):
        plan = Plan(
            plan_identifier=str(i),
            title=f"Issue {i}",
            body="",
            state=PlanState.OPEN,
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        issue = plan_to_issue(plan)
        plans_dict[i] = issue
        issues_list.append(issue)
        all_plans.append(plan)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues=plans_dict)
        github = FakeLocalGitHub(issues_data=issues_list)
        plan_service = build_fake_plan_list_service(all_plans)
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Act
        result = runner.invoke(cli, ["pr", "list", "--limit", "2"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output


def test_plan_list_combined_filters() -> None:
    """Test combining multiple filters."""
    # Arrange
    matching_plan = Plan(
        plan_identifier="1",
        title="Matching Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    wrong_state_plan = Plan(
        plan_identifier="2",
        title="Wrong State",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    wrong_labels_plan = Plan(
        plan_identifier="3",
        title="Wrong Labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/3",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={
                1: plan_to_issue(matching_plan),
                2: plan_to_issue(wrong_state_plan),
                3: plan_to_issue(wrong_labels_plan),
            }
        )
        github = FakeLocalGitHub(
            issues_data=[
                plan_to_issue(matching_plan),
                plan_to_issue(wrong_state_plan),
                plan_to_issue(wrong_labels_plan),
            ]
        )
        plan_service = build_fake_plan_list_service(
            [matching_plan, wrong_state_plan, wrong_labels_plan]
        )
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Act
        result = runner.invoke(
            cli,
            [
                "pr",
                "list",
                "--state",
                "open",
                "--label",
                "erk-plan",
                "--label",
                "bug",
            ],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output


def test_plan_list_empty_results() -> None:
    """Test querying with filters that match no issues."""
    # Arrange
    plan = Plan(
        plan_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan)])
        plan_service = build_fake_plan_list_service([plan])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Act
        result = runner.invoke(cli, ["pr", "list", "--state", "closed"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output
