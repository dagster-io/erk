"""Tests for plan list filtering functionality.

Tests state, labels, limit, and combined filters for plan list command.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.plan_store.types import PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import make_test_plan, plan_to_issue


def test_plan_list_no_filters() -> None:
    """Test listing all plan issues with no filters (defaults to open plans only)."""
    # Arrange - Create two OPEN plans (no filter defaults to open state)
    plan1 = make_test_plan("1", title="Issue 1", metadata={})
    plan2 = make_test_plan(
        "2",
        title="Issue 2",
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Use erk plan list for static output
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue 1" in result.output
        assert "#2" in result.output
        assert "Issue 2" in result.output


def test_plan_list_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    # Arrange
    open_plan = make_test_plan("1", title="Open Issue", metadata={})
    closed_plan = make_test_plan(
        "2",
        title="Closed Issue",
        state=PlanState.CLOSED,
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        github = FakeGitHub(issues_data=[plan_to_issue(open_plan), plan_to_issue(closed_plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for open issues
        result = runner.invoke(cli, ["plan", "list", "--state", "open"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Open Issue" in result.output
        assert "#2" not in result.output


def test_plan_list_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    # Arrange
    plan_with_both = make_test_plan(
        "1", title="Issue with both labels", labels=["erk-plan", "erk-queue"], metadata={}
    )
    plan_with_one = make_test_plan(
        "2",
        title="Issue with one label",
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(plan_with_both), 2: plan_to_issue(plan_with_one)}
        )
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan_with_both), plan_to_issue(plan_with_one)]
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for both labels (AND logic)
        result = runner.invoke(
            cli,
            ["plan", "list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue with both labels" in result.output
        assert "#2" not in result.output


def test_plan_list_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    # Arrange
    plans_dict: dict[int, IssueInfo] = {}
    issues_list: list[IssueInfo] = []
    for i in range(1, 6):
        plan = make_test_plan(
            str(i),
            title=f"Issue {i}",
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
        )
        issue = plan_to_issue(plan)
        plans_dict[i] = issue
        issues_list.append(issue)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues=plans_dict)
        github = FakeGitHub(issues_data=issues_list)
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list", "--limit", "2"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output


def test_plan_list_combined_filters() -> None:
    """Test combining multiple filters."""
    # Arrange
    matching_plan = make_test_plan(
        "1", title="Matching Issue", labels=["erk-plan", "bug"], metadata={}
    )
    wrong_state_plan = make_test_plan(
        "2",
        title="Wrong State",
        state=PlanState.CLOSED,
        labels=["erk-plan", "bug"],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    wrong_labels_plan = make_test_plan(
        "3",
        title="Wrong Labels",
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
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
        github = FakeGitHub(
            issues_data=[
                plan_to_issue(matching_plan),
                plan_to_issue(wrong_state_plan),
                plan_to_issue(wrong_labels_plan),
            ]
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(
            cli,
            [
                "plan",
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
        assert "Matching Issue" in result.output


def test_plan_list_empty_results() -> None:
    """Test querying with filters that match no issues."""
    # Arrange
    plan = make_test_plan("1", title="Issue", metadata={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list", "--state", "closed"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output
