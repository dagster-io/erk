"""Tests for `erk json pr ...` commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import (
    build_fake_plan_list_service,
    build_workspace_test_context,
)
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _plan_to_issue(plan: Plan) -> IssueInfo:
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
        author="test-user",
    )


def _make_remote(plan: Plan) -> FakeRemoteGitHub:
    issue = _plan_to_issue(plan)
    return FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues={issue.number: issue},
        issue_comments=None,
        pr_references=None,
    )


def test_machine_pr_list_returns_structured_json() -> None:
    plan = Plan(
        pr_identifier="42",
        title="Plan 42",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={42: _plan_to_issue(plan)})
        github = FakeLocalGitHub(issues_data=[_plan_to_issue(plan)])
        plan_service = build_fake_plan_list_service([plan])
        ctx = build_workspace_test_context(
            env,
            issues=issues,
            github=github,
            plan_list_service=plan_service,
        )

        result = runner.invoke(
            cli,
            ["json", "pr", "list"],
            obj=ctx,
            input="{}",
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["count"] == 1
    assert data["plans"][0]["plan_id"] == 42


def test_machine_pr_view_returns_structured_json() -> None:
    plan = Plan(
        pr_identifier="42",
        title="Plan 42",
        body="Full body",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan})
        ctx = build_workspace_test_context(
            env,
            plan_store=store,
            remote_github=_make_remote(plan),
        )

        result = runner.invoke(
            cli,
            ["json", "pr", "view"],
            obj=ctx,
            input=json.dumps({"identifier": "42", "full": True}),
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["plan_id"] == "42"
    assert data["title"] == "Plan 42"
    assert data["body"] == "Full body"


def test_human_pr_list_no_longer_accepts_json_flag() -> None:
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env)
        result = runner.invoke(cli, ["pr", "list", "--json"], obj=ctx)

    assert result.exit_code != 0
    assert "--json" in result.output


def test_human_pr_view_no_longer_accepts_json_flag() -> None:
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env)
        result = runner.invoke(cli, ["pr", "view", "42", "--json"], obj=ctx)

    assert result.exit_code != 0
    assert "--json" in result.output
