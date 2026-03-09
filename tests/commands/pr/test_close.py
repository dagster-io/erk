"""Tests for plan close command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo, PRReference
from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    format_plan_header_body_for_test,
    issue_info_to_pr_details,
)


def test_close_plan_with_plan_number() -> None:
    """Test closing a plan with plan number."""
    # Arrange
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
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
        store, fake_github = create_plan_store_with_plans({"42": plan_issue})
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
                    labels=["erk-pr", "erk-plan"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
            pr_references=None,
        )
        ctx = build_workspace_test_context(
            env, plan_store=store, issues=fake_github.issues, remote_github=fake_remote
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert 42 in fake_github.closed_prs
        # Verify PlannedPRBackend added a comment before closing
        assert any(num == 42 and "completed" in body for num, body in fake_github.pr_comments)


def test_close_plan_not_found() -> None:
    """Test closing a plan that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={},
            issue_comments=None,
            pr_references=None,
        )
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=fake_remote)

        # Act
        result = runner.invoke(cli, ["pr", "close", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Plan #999 not found" in result.output


def _make_issue_info(plan: Plan) -> IssueInfo:
    """Helper to convert Plan to IssueInfo for tests needing custom FakeGitHubIssues config."""
    state = "OPEN" if plan.state == PlanState.OPEN else "CLOSED"
    return IssueInfo(
        number=int(plan.pr_identifier),
        title=plan.title,
        body=plan.body,
        state=state,
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at.astimezone(UTC),
        updated_at=plan.updated_at.astimezone(UTC),
        author="test-author",
    )


def test_close_plan_closes_linked_open_prs() -> None:
    """Test closing a plan closes all OPEN PRs linked to the issue."""
    # Arrange
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    # Create linked PRs (one draft, one non-draft, both OPEN)
    open_draft_pr = PRReference(number=100, state="OPEN", is_draft=True)
    open_non_draft_pr = PRReference(number=101, state="OPEN", is_draft=False)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issue = _make_issue_info(plan_issue)
        # Create FakeGitHubIssues with both the plan issue and PR references
        fake_issues = FakeGitHubIssues(
            issues={42: issue},
            pr_references={42: [open_draft_pr, open_non_draft_pr]},
        )
        fake_github = FakeLocalGitHub(
            pr_details={42: issue_info_to_pr_details(issue)},
            issues_gateway=fake_issues,
        )
        store = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: issue},
            issue_comments=None,
            pr_references={42: [open_draft_pr, open_non_draft_pr]},
        )
        ctx = build_workspace_test_context(
            env, plan_store=store, github=fake_github, issues=fake_issues, remote_github=fake_remote
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert "Closed 2 linked PR(s): #100, #101" in result.output
        # Verify both linked PRs were closed via RemoteGitHub
        assert any(cp.number == 100 for cp in fake_remote.closed_prs)
        assert any(cp.number == 101 for cp in fake_remote.closed_prs)


def test_close_plan_skips_closed_and_merged_prs() -> None:
    """Test closing a plan skips CLOSED and MERGED PRs, only closes OPEN."""
    # Arrange
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    # Create PRs in various states
    open_pr = PRReference(number=100, state="OPEN", is_draft=False)
    closed_pr = PRReference(number=101, state="CLOSED", is_draft=False)
    merged_pr = PRReference(number=102, state="MERGED", is_draft=False)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issue = _make_issue_info(plan_issue)
        fake_issues = FakeGitHubIssues(
            issues={42: issue},
            pr_references={42: [open_pr, closed_pr, merged_pr]},
        )
        fake_github = FakeLocalGitHub(
            pr_details={42: issue_info_to_pr_details(issue)},
            issues_gateway=fake_issues,
        )
        store = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: issue},
            issue_comments=None,
            pr_references={42: [open_pr, closed_pr, merged_pr]},
        )
        ctx = build_workspace_test_context(
            env, plan_store=store, github=fake_github, issues=fake_issues, remote_github=fake_remote
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert "Closed 1 linked PR(s): #100" in result.output
        # Only the OPEN linked PR should be closed via RemoteGitHub
        assert any(cp.number == 100 for cp in fake_remote.closed_prs)
        assert not any(cp.number == 101 for cp in fake_remote.closed_prs)
        assert not any(cp.number == 102 for cp in fake_remote.closed_prs)


def test_close_plan_no_linked_prs() -> None:
    """Test closing a plan with no linked PRs works without error."""
    # Arrange
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
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
        issue = _make_issue_info(plan_issue)
        fake_issues = FakeGitHubIssues(
            issues={42: issue},
            pr_references={},  # No linked PRs
        )
        fake_github = FakeLocalGitHub(
            pr_details={42: issue_info_to_pr_details(issue)},
            issues_gateway=fake_issues,
        )
        store = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: issue},
            issue_comments=None,
            pr_references={},  # No linked PRs
        )
        ctx = build_workspace_test_context(
            env, plan_store=store, github=fake_github, issues=fake_issues, remote_github=fake_remote
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        # No linked PR closing message should appear
        assert "linked PR(s)" not in result.output


def test_close_plan_invalid_identifier() -> None:
    """Test closing a plan with invalid identifier fails with helpful error."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={},
            issue_comments=None,
            pr_references=None,
        )
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=fake_remote)

        # Act
        result = runner.invoke(cli, ["pr", "close", "not-a-number"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Invalid plan number or URL" in result.output
        assert "not-a-number" in result.output


def test_close_plan_invalid_url_format() -> None:
    """Test closing a plan with invalid URL format gives specific error."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={},
            issue_comments=None,
            pr_references=None,
        )
        ctx = build_workspace_test_context(env, plan_store=store, remote_github=fake_remote)

        # Act - GitHub URL but pointing to pulls instead of issues
        result = runner.invoke(
            cli, ["pr", "close", "https://github.com/owner/repo/pulls/42"], obj=ctx
        )

        # Assert
        assert result.exit_code != 0
        assert "Invalid plan number or URL" in result.output
        assert "https://github.com/owner/repo/issues/456" in result.output


def test_close_plan_reports_closed_prs() -> None:
    """Test closing a plan reports the closed PRs in output."""
    # Arrange
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    # Create multiple linked OPEN PRs
    pr1 = PRReference(number=100, state="OPEN", is_draft=False)
    pr2 = PRReference(number=200, state="OPEN", is_draft=False)
    pr3 = PRReference(number=300, state="OPEN", is_draft=False)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issue = _make_issue_info(plan_issue)
        fake_issues = FakeGitHubIssues(
            issues={42: issue},
            pr_references={42: [pr1, pr2, pr3]},
        )
        fake_github = FakeLocalGitHub(
            pr_details={42: issue_info_to_pr_details(issue)},
            issues_gateway=fake_issues,
        )
        store = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        fake_remote = FakeRemoteGitHub(
            authenticated_user="test-user",
            default_branch_name="main",
            default_branch_sha="abc123",
            next_pr_number=1,
            dispatch_run_id="run-1",
            issues={42: issue},
            issue_comments=None,
            pr_references={42: [pr1, pr2, pr3]},
        )
        ctx = build_workspace_test_context(
            env, plan_store=store, github=fake_github, issues=fake_issues, remote_github=fake_remote
        )

        # Act
        result = runner.invoke(cli, ["pr", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed 3 linked PR(s): #100, #200, #300" in result.output


def test_close_plan_with_objective_invokes_update() -> None:
    """Test closing a plan linked to an objective invokes the objective update."""
    # Arrange - body must include plan-header with objective_issue so
    # PlannedPRBackend._convert_to_plan() extracts objective_id correctly
    body_with_header = format_plan_header_body_for_test(objective_issue=99) + "\nPlan content"
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body=body_with_header,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"issue_body": body_with_header},
        objective_id=99,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        executor = FakePromptExecutor()
        store, fake_github = create_plan_store_with_plans({"42": plan_issue})
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
                    labels=["erk-pr", "erk-plan"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
            pr_references=None,
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
        assert "Closed plan #42" in result.output
        # Verify the objective update command was invoked
        assert len(executor.executed_commands) == 1
        executed_cmd = executor.executed_commands[0][0]
        assert "/erk:objective-update-with-closed-plan" in executed_cmd
        assert "--plan 42" in executed_cmd
        assert "--objective 99" in executed_cmd


def test_close_plan_without_objective_skips_update() -> None:
    """Test closing a plan without an objective does not invoke objective update."""
    # Arrange
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body="This is a test issue",
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
        executor = FakePromptExecutor()
        store, fake_github = create_plan_store_with_plans({"42": plan_issue})
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
                    labels=["erk-pr", "erk-plan"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
            pr_references=None,
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
        assert "Closed plan #42" in result.output
        # No objective update should have been invoked
        assert len(executor.executed_commands) == 0


def test_close_plan_objective_update_failure_does_not_break_close() -> None:
    """Test that a failing objective update does not prevent plan close from succeeding."""
    # Arrange - body must include plan-header with objective_issue so
    # PlannedPRBackend._convert_to_plan() extracts objective_id correctly
    body_with_header = format_plan_header_body_for_test(objective_issue=99) + "\nPlan content"
    plan_issue = Plan(
        pr_identifier="42",
        title="Test Issue",
        body=body_with_header,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"issue_body": body_with_header},
        objective_id=99,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        executor = FakePromptExecutor(command_should_fail=True)
        store, fake_github = create_plan_store_with_plans({"42": plan_issue})
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
                    labels=["erk-pr", "erk-plan"],
                    assignees=[],
                    created_at=datetime(2024, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2024, 1, 2, tzinfo=UTC),
                    author="test-author",
                )
            },
            issue_comments=None,
            pr_references=None,
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
        assert "Closed plan #42" in result.output
        assert "Objective update failed" in result.output
