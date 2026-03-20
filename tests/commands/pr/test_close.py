"""Tests for plan close command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.tests.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import (
    create_pr_backend_with_plans,
    format_plan_header_body_for_test,
)


def test_close_pr_with_pr_number() -> None:
    """Test closing a pr with pr number."""
    # Arrange
    pr_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, fake_github = create_pr_backend_with_plans({"42": pr_issue})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Issue",
                    body="This is a test issue",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/42",
                    labels=["erk-pr"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env, plan_store=store, issues=fake_github.issues, remote_github=fake_remote
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed PR #42" in result.output
        assert 42 in fake_github.closed_prs
        # Verify ManagedGitHubPrBackend added a comment before closing
        assert any(num == 42 and "completed" in body for num, body in fake_github.pr_comments)


def test_close_pr_not_found() -> None:
    """Test closing a pr that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_pr_backend_with_plans({})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={},
            issue_comments=None,
        )
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=fake_remote)

        # Act
        result = runner.invoke(cli, ["pr", "close", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "PR #999 not found" in result.output


def test_close_pr_invalid_identifier() -> None:
    """Test closing a pr with invalid identifier fails with helpful error."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_pr_backend_with_plans({})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={},
            issue_comments=None,
        )
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=fake_remote)

        # Act
        result = runner.invoke(cli, ["pr", "close", "not-a-number"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Invalid PR number or URL" in result.output
        assert "not-a-number" in result.output


def test_close_pr_invalid_url_format() -> None:
    """Test closing a pr with invalid URL format gives specific error."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_pr_backend_with_plans({})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={},
            issue_comments=None,
        )
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=fake_remote)

        # Act - GitHub URL but pointing to pulls instead of issues
        result = runner.invoke(
            cli, ["pr", "close", "https://github.com/owner/repo/pulls/42"], obj=ctx
        )

        # Assert
        assert result.exit_code != 0
        assert "Invalid PR number or URL" in result.output
        assert "https://github.com/owner/repo/issues/456" in result.output


def test_close_pr_with_objective_invokes_update() -> None:
    """Test closing a pr linked to an objective invokes the objective update."""
    # Arrange - body must include plan-header with objective_issue so
    # ManagedGitHubPrBackend._convert_to_plan() extracts objective_id correctly
    body_with_header = format_plan_header_body_for_test(objective_issue=99) + "\nPlan content"
    pr_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body=body_with_header,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"issue_body": body_with_header},
        objective_id=99,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        executor = FakePromptExecutor()
        store, fake_github = create_pr_backend_with_plans({"42": pr_issue})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Issue",
                    body=body_with_header,
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/42",
                    labels=["erk-pr"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env,
            plan_store=store,
            issues=fake_github.issues,
            prompt_executor=executor,
            remote_github=fake_remote,
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed PR #42" in result.output
        # Verify the objective update command was invoked
        assert len(executor.executed_commands) == 1
        executed_cmd = executor.executed_commands[0][0]
        assert "/erk:objective-update-with-closed-plan" in executed_cmd
        assert "--plan 42" in executed_cmd
        assert "--objective 99" in executed_cmd


def test_close_pr_without_objective_skips_update() -> None:
    """Test closing a pr without an objective does not invoke objective update."""
    # Arrange
    pr_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        executor = FakePromptExecutor()
        store, fake_github = create_pr_backend_with_plans({"42": pr_issue})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Issue",
                    body="This is a test issue",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/42",
                    labels=["erk-pr"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env,
            plan_store=store,
            issues=fake_github.issues,
            prompt_executor=executor,
            remote_github=fake_remote,
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed PR #42" in result.output
        # No objective update should have been invoked
        assert len(executor.executed_commands) == 0


def test_close_pr_objective_update_failure_does_not_break_close() -> None:
    """Test that a failing objective update does not prevent plan close from succeeding."""
    # Arrange - body must include plan-header with objective_issue so
    # ManagedGitHubPrBackend._convert_to_plan() extracts objective_id correctly
    body_with_header = format_plan_header_body_for_test(objective_issue=99) + "\nPlan content"
    pr_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body=body_with_header,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"issue_body": body_with_header},
        objective_id=99,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        executor = FakePromptExecutor(command_should_fail=True)
        store, fake_github = create_pr_backend_with_plans({"42": pr_issue})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={
                42: IssueInfo(
                    number=42,
                    title="Test Issue",
                    body=body_with_header,
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/42",
                    labels=["erk-pr"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
        )
        ctx = build_workspace_test_context(
            env,
            plan_store=store,
            issues=fake_github.issues,
            prompt_executor=executor,
            remote_github=fake_remote,
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert - close still succeeds even though objective update failed
        assert result.exit_code == 0
        assert "Closed PR #42" in result.output
        assert "Objective update failed" in result.output
