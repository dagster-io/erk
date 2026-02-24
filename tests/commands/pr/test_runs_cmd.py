"""Tests for plan runs command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import WorkflowRun
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_plan(*, plan_id: str, branch_name: str) -> Plan:
    """Create a Plan with plan-header metadata containing branch_name."""
    header_body = format_plan_header_body_for_test(branch_name=branch_name)
    return Plan(
        plan_identifier=plan_id,
        title="Test Plan",
        body=header_body + "\n\nPlan content here",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/" + plan_id,
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )


def _make_issue_info(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for FakeGitHubIssues."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.astimezone(UTC),
        updated_at=plan.updated_at.astimezone(UTC),
        author="test-author",
    )


def _make_workflow_run(
    *,
    run_id: str,
    branch: str,
    status: str = "completed",
    conclusion: str | None = "success",
) -> WorkflowRun:
    """Create a WorkflowRun for testing."""
    return WorkflowRun(
        run_id=run_id,
        status=status,
        conclusion=conclusion,
        branch=branch,
        head_sha="abc123",
        created_at=datetime(2024, 1, 15, 12, 30, tzinfo=UTC),
    )


def test_runs_shows_table_with_matching_runs() -> None:
    """Happy path: plan with matching workflow runs shows table."""
    plan = _make_plan(plan_id="42", branch_name="plnd/plan-test-feature")
    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
    )
    store = GitHubPlanStore(fake_issues)

    runs = [
        _make_workflow_run(run_id="100", branch="plnd/plan-test-feature"),
        _make_workflow_run(
            run_id="101",
            branch="plnd/plan-test-feature",
            status="in_progress",
            conclusion=None,
        ),
    ]

    github = FakeGitHub(workflow_runs=runs)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues, github=github)

        result = runner.invoke(cli, ["pr", "runs", "42"], obj=ctx)

        assert result.exit_code == 0
        # Table is rendered to stderr by Rich Console, check stderr output
        assert "100" in result.output or "100" in (result.stderr_bytes or b"").decode()


def test_runs_no_runs_found() -> None:
    """Plan with branch that has no runs shows empty message."""
    plan = _make_plan(plan_id="42", branch_name="plnd/plan-no-runs")
    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
    )
    store = GitHubPlanStore(fake_issues)

    # No workflow runs configured
    github = FakeGitHub(workflow_runs=[])

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues, github=github)

        result = runner.invoke(cli, ["pr", "runs", "42"], obj=ctx)

        assert result.exit_code == 0
        assert "No workflow runs found" in result.output


def test_runs_plan_not_found() -> None:
    """Invalid identifier shows error."""
    fake_issues = FakeGitHubIssues(issues={})
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["pr", "runs", "999"], obj=ctx)

        assert result.exit_code == 1
        assert "not found" in result.output


def test_runs_no_branch_metadata() -> None:
    """Plan without branch_name metadata shows error."""
    # Create plan without branch_name in header
    header_body = format_plan_header_body_for_test()
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body=header_body + "\n\nPlan content",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        result = runner.invoke(cli, ["pr", "runs", "42"], obj=ctx)

        assert result.exit_code == 1
        assert "no branch_name" in result.output


def test_runs_json_output() -> None:
    """--json flag produces valid JSON output."""
    plan = _make_plan(plan_id="42", branch_name="plnd/plan-json-test")
    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
    )
    store = GitHubPlanStore(fake_issues)

    runs = [
        _make_workflow_run(run_id="200", branch="plnd/plan-json-test"),
    ]

    github = FakeGitHub(workflow_runs=runs)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues, github=github)

        result = runner.invoke(cli, ["pr", "runs", "42", "--json"], obj=ctx)

        assert result.exit_code == 0

        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1

        entry = data[0]
        assert "workflow" in entry
        assert "run_id" in entry
        assert "status" in entry
        assert "conclusion" in entry
        assert "created_at" in entry
