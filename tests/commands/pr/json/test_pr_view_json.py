"""Tests for erk json pr view machine command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _plan_to_issue_info(plan: Plan) -> IssueInfo:
    return IssueInfo(
        number=int(plan.pr_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        author="test-author",
    )


def _make_fake_remote(*plans: Plan) -> FakeRemoteGitHub:
    issues = {int(p.pr_identifier): _plan_to_issue_info(p) for p in plans}
    return FakeRemoteGitHub(
        authenticated_user="test-author",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=issues,
        issue_comments=None,
        pr_references=None,
    )


def _make_plan(pr_id: str, title: str) -> Plan:
    return Plan(
        pr_identifier=pr_id,
        title=title,
        body="Plan body",
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{pr_id}",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )


def test_json_pr_view_success() -> None:
    """JSON output on successful view via erk json pr view."""
    plan = _make_plan("42", "Test Plan")
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan})
        ctx = build_workspace_test_context(
            env, plan_store=store, remote_github=_make_fake_remote(plan)
        )

        result = runner.invoke(
            cli,
            ["json", "pr", "view"],
            input='{"identifier": "42"}',
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["plan_id"] == "42"
        assert data["title"] == "Test Plan"
        assert data["state"] == "OPEN"


def test_json_pr_view_not_found() -> None:
    """JSON error when plan not found via erk json pr view."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=_make_fake_remote())

        result = runner.invoke(
            cli,
            ["json", "pr", "view"],
            input='{"identifier": "999"}',
            obj=ctx,
        )

        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error_type"] == "not_found"


def test_json_pr_view_schema() -> None:
    """--schema flag outputs valid schema document."""
    runner = CliRunner()
    result = runner.invoke(cli, ["json", "pr", "view", "--schema"])

    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["command"] == "pr_view"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert "error_schema" in doc
