"""Unit tests for pr dispatch operation."""

from datetime import UTC, datetime

from erk.cli.commands.pr.dispatch.operation import (
    PrDispatchRequest,
    PrDispatchResult,
    run_pr_dispatch,
)
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import MetadataBlock, render_metadata_block
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.tests.shared_context import context_for_test


def _make_plan_body(*, branch_name: str) -> str:
    """Build a plan PR body with proper plan-header metadata."""
    plan_header = render_metadata_block(
        MetadataBlock(
            key="plan-header",
            data={
                "schema_version": "2",
                "created_at": "2024-01-01T00:00:00+00:00",
                "created_by": "testuser",
                "branch_name": branch_name,
            },
        )
    )
    return build_plan_stage_body(
        plan_header,
        "# Plan: Test Plan\n\n- Step 1: Do something\n- Step 2: Do something else",
        summary=None,
    )


def _make_issue(
    *,
    number: int,
    title: str,
    body: str,
    state: str,
    url: str,
) -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=url,
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        author="testuser",
    )


def test_dispatch_returns_result_on_success() -> None:
    """Happy path: valid plan PR returns PrDispatchResult with all fields."""
    plan_body = _make_plan_body(branch_name="plnd/test-plan")
    issue = _make_issue(
        number=42,
        title="[erk-pr] Test Plan",
        body=plan_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/pull/42",
    )

    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=100,
        dispatch_run_id="run-12345",
        issues={42: issue},
        issue_comments=None,
        pr_references=None,
    )

    ctx = context_for_test(remote_github=remote)
    request = PrDispatchRequest(pr_number=42, base_branch=None, ref=None)

    result = run_pr_dispatch(ctx, request, owner="test-owner", repo_name="test-repo")

    assert isinstance(result, PrDispatchResult)
    assert result.pr_number == 42
    assert result.plan_title == "[erk-pr] Test Plan"
    assert result.plan_url == "https://github.com/test-owner/test-repo/pull/42"
    assert result.impl_pr_number == 42
    assert result.impl_pr_url == "https://github.com/test-owner/test-repo/pull/42"
    assert result.workflow_run_id == "run-12345"
    assert "actions/runs/run-12345" in result.workflow_url

    # Verify workflow was dispatched
    assert len(remote.dispatched_workflows) == 1
    wf = remote.dispatched_workflows[0]
    assert wf.inputs["plan_backend"] == "planned_pr"
    assert wf.inputs["plan_id"] == "42"
    assert wf.inputs["branch_name"] == "plnd/test-plan"

    # Verify impl-context files were committed
    assert len(remote.created_file_commits) > 0


def test_dispatch_returns_error_when_pr_not_found() -> None:
    """Returns MachineCommandError when PR doesn't exist."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=100,
        dispatch_run_id="run-12345",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )

    ctx = context_for_test(remote_github=remote)
    request = PrDispatchRequest(pr_number=999, base_branch=None, ref=None)

    result = run_pr_dispatch(ctx, request, owner="test-owner", repo_name="test-repo")

    assert isinstance(result, MachineCommandError)
    assert result.error_type == "not_found"
    assert "999" in result.message


def test_dispatch_returns_error_when_missing_title_prefix() -> None:
    """Returns MachineCommandError when PR lacks [erk-pr] title prefix."""
    issue = _make_issue(
        number=42,
        title="Regular PR without prefix",
        body="some body",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/pull/42",
    )

    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=100,
        dispatch_run_id="run-12345",
        issues={42: issue},
        issue_comments=None,
        pr_references=None,
    )

    ctx = context_for_test(remote_github=remote)
    request = PrDispatchRequest(pr_number=42, base_branch=None, ref=None)

    result = run_pr_dispatch(ctx, request, owner="test-owner", repo_name="test-repo")

    assert isinstance(result, MachineCommandError)
    assert result.error_type == "invalid_pr"
    assert "[erk-pr]" in result.message


def test_dispatch_returns_error_when_pr_not_open() -> None:
    """Returns MachineCommandError when PR is not OPEN."""
    issue = _make_issue(
        number=42,
        title="[erk-pr] Closed Plan",
        body="some body",
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/pull/42",
    )

    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=100,
        dispatch_run_id="run-12345",
        issues={42: issue},
        issue_comments=None,
        pr_references=None,
    )

    ctx = context_for_test(remote_github=remote)
    request = PrDispatchRequest(pr_number=42, base_branch=None, ref=None)

    result = run_pr_dispatch(ctx, request, owner="test-owner", repo_name="test-repo")

    assert isinstance(result, MachineCommandError)
    assert result.error_type == "pr_not_open"
    assert "CLOSED" in result.message


def test_dispatch_returns_error_when_branch_not_determinable() -> None:
    """Returns MachineCommandError when branch cannot be extracted from plan metadata."""
    issue = _make_issue(
        number=42,
        title="[erk-pr] No Branch Plan",
        body="Body without plan-header metadata block",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/pull/42",
    )

    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=100,
        dispatch_run_id="run-12345",
        issues={42: issue},
        issue_comments=None,
        pr_references=None,
    )

    ctx = context_for_test(remote_github=remote)
    request = PrDispatchRequest(pr_number=42, base_branch=None, ref=None)

    result = run_pr_dispatch(ctx, request, owner="test-owner", repo_name="test-repo")

    assert isinstance(result, MachineCommandError)
    assert result.error_type == "branch_not_determinable"
    assert "branch name" in result.message


def test_dispatch_result_to_json_dict() -> None:
    """Verify PrDispatchResult.to_json_dict() includes all fields."""
    result = PrDispatchResult(
        pr_number=42,
        plan_title="[erk-pr] Test Plan",
        plan_url="https://github.com/owner/repo/pull/42",
        impl_pr_number=42,
        impl_pr_url="https://github.com/owner/repo/pull/42",
        workflow_run_id="run-99",
        workflow_url="https://github.com/owner/repo/actions/runs/run-99",
    )

    json_dict = result.to_json_dict()

    assert json_dict["pr_number"] == 42
    assert json_dict["plan_title"] == "[erk-pr] Test Plan"
    assert json_dict["plan_url"] == "https://github.com/owner/repo/pull/42"
    assert json_dict["impl_pr_number"] == 42
    assert json_dict["impl_pr_url"] == "https://github.com/owner/repo/pull/42"
    assert json_dict["workflow_run_id"] == "run-99"
    assert json_dict["workflow_url"] == "https://github.com/owner/repo/actions/runs/run-99"


def test_dispatch_result_to_json_dict_with_none_impl() -> None:
    """Verify to_json_dict() handles None impl fields correctly."""
    result = PrDispatchResult(
        pr_number=42,
        plan_title="[erk-pr] Test Plan",
        plan_url="https://github.com/owner/repo/pull/42",
        impl_pr_number=None,
        impl_pr_url=None,
        workflow_run_id="run-99",
        workflow_url="https://github.com/owner/repo/actions/runs/run-99",
    )

    json_dict = result.to_json_dict()

    assert json_dict["impl_pr_number"] is None
    assert json_dict["impl_pr_url"] is None


def test_dispatch_uses_explicit_base_branch() -> None:
    """When base_branch is provided, it should be used instead of default."""
    plan_body = _make_plan_body(branch_name="plnd/test-plan")
    issue = _make_issue(
        number=42,
        title="[erk-pr] Test Plan",
        body=plan_body,
        state="OPEN",
        url="https://github.com/test-owner/test-repo/pull/42",
    )

    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=100,
        dispatch_run_id="run-12345",
        issues={42: issue},
        issue_comments=None,
        pr_references=None,
    )

    ctx = context_for_test(remote_github=remote)
    request = PrDispatchRequest(pr_number=42, base_branch="develop", ref=None)

    result = run_pr_dispatch(ctx, request, owner="test-owner", repo_name="test-repo")

    assert isinstance(result, PrDispatchResult)
    wf = remote.dispatched_workflows[0]
    assert wf.inputs["base_branch"] == "develop"
