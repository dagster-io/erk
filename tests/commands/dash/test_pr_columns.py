"""Tests for PR status column display in plan list command.

Tests PR emoji display (open 👀, draft 🚧, merged 🎉, closed ⛔, conflict 💥).
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_plan_list_pr_column_no_pr_linked() -> None:
    """Test PR column shows '-' when no PR is linked to issue."""
    # Arrange
    plan = Plan(
        plan_identifier="106",
        title="Plan without PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/106",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 106},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={106: plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan)])
        # No PR linkages configured
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["pr", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#106" in result.output
        # PR and Checks columns should both show "-"
        # Can't easily assert the exact column position, but verifying no emojis appear
        assert "👀" not in result.output
        assert "🚧" not in result.output
        assert "🎉" not in result.output
        assert "⛔" not in result.output
