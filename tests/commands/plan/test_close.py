"""Tests for plan close command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo, PRReference
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_close_plan_with_issue_number() -> None:
    """Test closing a plan with issue number."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, fake_issues = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert 42 in fake_issues.closed_issues
        # Verify GitHubPlanStore added a comment before closing
        assert any(num == 42 and "completed" in body for num, body, _ in fake_issues.added_comments)


def test_close_plan_not_found() -> None:
    """Test closing a plan that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "close", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Issue #999 not found" in result.output


def _make_issue_info(plan: Plan) -> IssueInfo:
    """Helper to convert Plan to IssueInfo for tests needing custom FakeGitHubIssues config."""
    state = "OPEN" if plan.state == PlanState.OPEN else "CLOSED"
    return IssueInfo(
        number=int(plan.plan_identifier),
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
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    # Create linked PRs (one draft, one non-draft, both OPEN)
    open_draft_pr = PRReference(number=100, state="OPEN", is_draft=True)
    open_non_draft_pr = PRReference(number=101, state="OPEN", is_draft=False)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHub()
        # Create FakeGitHubIssues with both the plan issue and PR references
        fake_issues = FakeGitHubIssues(
            issues={42: _make_issue_info(plan_issue)},
            pr_references={42: [open_draft_pr, open_non_draft_pr]},
        )
        store = GitHubPlanStore(fake_issues)
        ctx = build_workspace_test_context(env, plan_store=store, github=github, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert "Closed 2 linked PR(s): #100, #101" in result.output
        # Verify both PRs were closed via FakeGitHub
        assert 100 in github.closed_prs
        assert 101 in github.closed_prs


def test_close_plan_skips_closed_and_merged_prs() -> None:
    """Test closing a plan skips CLOSED and MERGED PRs, only closes OPEN."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    # Create PRs in various states
    open_pr = PRReference(number=100, state="OPEN", is_draft=False)
    closed_pr = PRReference(number=101, state="CLOSED", is_draft=False)
    merged_pr = PRReference(number=102, state="MERGED", is_draft=False)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHub()
        fake_issues = FakeGitHubIssues(
            issues={42: _make_issue_info(plan_issue)},
            pr_references={42: [open_pr, closed_pr, merged_pr]},
        )
        store = GitHubPlanStore(fake_issues)
        ctx = build_workspace_test_context(env, plan_store=store, github=github, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        assert "Closed 1 linked PR(s): #100" in result.output
        # Only the OPEN PR should be closed
        assert github.closed_prs == [100]


def test_close_plan_no_linked_prs() -> None:
    """Test closing a plan with no linked PRs works without error."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHub()
        fake_issues = FakeGitHubIssues(
            issues={42: _make_issue_info(plan_issue)},
            pr_references={},  # No linked PRs
        )
        store = GitHubPlanStore(fake_issues)
        ctx = build_workspace_test_context(env, plan_store=store, github=github, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed plan #42" in result.output
        # No PR closing message should appear
        assert "linked PR(s)" not in result.output
        assert github.closed_prs == []


def test_close_plan_invalid_identifier() -> None:
    """Test closing a plan with invalid identifier fails with helpful error."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "close", "not-a-number"], obj=ctx)

        # Assert
        assert result.exit_code != 0
        assert "Invalid issue number or URL" in result.output
        assert "not-a-number" in result.output


def test_close_plan_invalid_url_format() -> None:
    """Test closing a plan with invalid URL format gives specific error."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - GitHub URL but pointing to pulls instead of issues
        result = runner.invoke(
            cli, ["plan", "close", "https://github.com/owner/repo/pulls/42"], obj=ctx
        )

        # Assert
        assert result.exit_code != 0
        assert "Invalid issue number or URL" in result.output
        assert "https://github.com/owner/repo/issues/456" in result.output


def test_close_plan_reports_closed_prs() -> None:
    """Test closing a plan reports the closed PRs in output."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    # Create multiple linked OPEN PRs
    pr1 = PRReference(number=100, state="OPEN", is_draft=False)
    pr2 = PRReference(number=200, state="OPEN", is_draft=False)
    pr3 = PRReference(number=300, state="OPEN", is_draft=False)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        github = FakeGitHub()
        fake_issues = FakeGitHubIssues(
            issues={42: _make_issue_info(plan_issue)},
            pr_references={42: [pr1, pr2, pr3]},
        )
        store = GitHubPlanStore(fake_issues)
        ctx = build_workspace_test_context(env, plan_store=store, github=github, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "close", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Closed 3 linked PR(s): #100, #200, #300" in result.output
