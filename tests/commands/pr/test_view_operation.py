"""Tests for pr view core operation."""

from datetime import UTC, datetime

import pytest
from click.testing import CliRunner

from erk.cli.commands.pr.view_operation import PrViewRequest, run_pr_view
from erk_shared.agentclick.errors import AgentCliError
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _plan_to_issue_info(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for FakeRemoteGitHub."""
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
    """Build FakeRemoteGitHub with given plans as issues."""
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


def _make_plan(
    pr_id: str,
    title: str,
    body: str,
) -> Plan:
    return Plan(
        pr_identifier=pr_id,
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{pr_id}",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )


def test_run_pr_view_returns_result() -> None:
    """run_pr_view returns PrViewResult with plan data."""
    plan = _make_plan("42", "Test Plan", "Plan body text")
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan})
        ctx = build_workspace_test_context(
            env, plan_store=store, remote_github=_make_fake_remote(plan)
        )

        request = PrViewRequest(identifier="42")
        result = run_pr_view(request, ctx=ctx)

        assert result.plan_id == "42"
        assert result.title == "Test Plan"
        assert result.state == "OPEN"
        assert result.body is None  # full=False by default


def test_run_pr_view_full_includes_body() -> None:
    """run_pr_view with full=True includes plan body."""
    plan = _make_plan("42", "Test Plan", "Plan body text")
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan})
        ctx = build_workspace_test_context(
            env, plan_store=store, remote_github=_make_fake_remote(plan)
        )

        request = PrViewRequest(identifier="42", full=True)
        result = run_pr_view(request, ctx=ctx)

        assert result.body == "Plan body text"


def test_run_pr_view_not_found_raises() -> None:
    """run_pr_view raises AgentCliError for missing plan."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=_make_fake_remote())

        request = PrViewRequest(identifier="999")
        with pytest.raises(AgentCliError) as exc_info:
            run_pr_view(request, ctx=ctx)

        assert exc_info.value.error_type == "not_found"


def test_run_pr_view_no_identifier_no_branch_raises() -> None:
    """run_pr_view raises AgentCliError when no identifier and branch can't infer."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(
            env,
            plan_store=store,
            remote_github=_make_fake_remote(),
            current_branch="master",
        )

        request = PrViewRequest()
        with pytest.raises(AgentCliError) as exc_info:
            run_pr_view(request, ctx=ctx)

        assert exc_info.value.error_type == "invalid_input"
