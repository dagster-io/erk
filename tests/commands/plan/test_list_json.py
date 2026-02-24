"""Tests for plan list --json-output command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
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
        author="test-user",
    )


def test_plan_list_json_output_valid_json() -> None:
    """Test that --json-output produces valid parseable JSON."""
    plan = Plan(
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
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: _plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[_plan_to_issue(plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--json-output"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "plans" in data
        assert "total_count" in data


def test_plan_list_json_schema() -> None:
    """Test JSON schema has expected top-level and nested fields."""
    plan = Plan(
        plan_identifier="42",
        title="Schema Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={42: _plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[_plan_to_issue(plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--json-output"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_count"] == 1

        entry = data["plans"][0]
        # Top-level fields
        assert entry["plan_id"] == 42
        assert entry["title"] == "Schema Test Plan"
        assert entry["author"] == "test-user"
        assert "created_at" in entry

        # Grouped sub-objects
        assert "pr" in entry
        assert "number" in entry["pr"]
        assert "url" in entry["pr"]
        assert "state" in entry["pr"]

        assert "location" in entry
        assert "exists_locally" in entry["location"]
        assert "worktree_branch" in entry["location"]

        assert "workflow_run" in entry
        assert "run_id" in entry["workflow_run"]
        assert "status" in entry["workflow_run"]

        assert "comments" in entry
        assert "resolved" in entry["comments"]
        assert "total" in entry["comments"]


def test_plan_list_json_empty_results() -> None:
    """Test --json-output with no matching plans returns empty array."""
    plan = Plan(
        plan_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: _plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[_plan_to_issue(plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--json-output", "--state", "closed"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["plans"] == []
        assert data["total_count"] == 0


def test_plan_list_json_multiple_plans() -> None:
    """Test JSON output with multiple plans."""
    plan1 = Plan(
        plan_identifier="1",
        title="First Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    plan2 = Plan(
        plan_identifier="2",
        title="Second Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: _plan_to_issue(plan1), 2: _plan_to_issue(plan2)})
        github = FakeGitHub(issues_data=[_plan_to_issue(plan1), _plan_to_issue(plan2)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--json-output"], obj=ctx)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_count"] == 2
        plan_ids = {p["plan_id"] for p in data["plans"]}
        assert plan_ids == {1, 2}
