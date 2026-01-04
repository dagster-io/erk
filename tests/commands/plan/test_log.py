"""Tests for plan log command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata import (
    create_implementation_status_block,
    create_plan_block,
    create_submission_queued_block,
    create_workflow_started_block,
    render_metadata_block,
)
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


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


def test_log_displays_timeline_chronologically() -> None:
    """Test log command displays events in chronological order."""
    # Arrange: Create plan and comments with metadata blocks
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    # Create metadata blocks (intentionally out of order to test sorting)
    workflow_block = create_workflow_started_block(
        started_at="2024-01-15T12:35:00Z",
        workflow_run_id="123456",
        workflow_run_url="https://github.com/owner/repo/actions/runs/123456",
        issue_number=42,
    )

    plan_block = create_plan_block(
        issue_number=42,
        worktree_name="test-plan",
        timestamp="2024-01-15T12:30:00Z",
    )

    submission_block = create_submission_queued_block(
        queued_at="2024-01-15T12:32:00Z",
        submitted_by="user",
        issue_number=42,
        validation_results={"issue_is_open": True},
        expected_workflow="implement-plan",
    )

    # Create comments with rendered blocks (out of chronological order)
    comment1 = render_metadata_block(workflow_block)
    comment2 = render_metadata_block(plan_block)
    comment3 = render_metadata_block(submission_block)

    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
        comments={42: [comment1, comment2, comment3]},
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Plan #42 Event Timeline" in result.output

        # Verify chronological order (plan created → queued → workflow started)
        output_lines = result.output.split("\n")

        # Find event lines (lines with timestamps)
        event_lines = [line for line in output_lines if "[2024-" in line]

        assert len(event_lines) == 3

        # Verify order by checking timestamps
        assert "12:30:00" in event_lines[0]  # Plan created first
        assert "12:32:00" in event_lines[1]  # Queued second
        assert "12:35:00" in event_lines[2]  # Workflow started third


def test_log_json_output() -> None:
    """Test log command with --json flag outputs valid JSON."""
    # Arrange
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    plan_block = create_plan_block(
        issue_number=42,
        worktree_name="test-plan",
        timestamp="2024-01-15T12:30:00Z",
    )

    comment = render_metadata_block(plan_block)

    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
        comments={42: [comment]},
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42", "--json"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Parse JSON output
        events = json.loads(result.output)

        assert isinstance(events, list)
        assert len(events) == 1

        event = events[0]
        assert event["event_type"] == "plan-created"
        assert event["timestamp"] == "2024-01-15T12:30:00Z"
        assert event["metadata"]["worktree_name"] == "test-plan"


def test_log_with_no_events() -> None:
    """Test log command when issue has no comments."""
    # Arrange
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
        comments={42: []},  # No comments
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No events found for plan #42" in result.output


def test_log_with_all_event_types() -> None:
    """Test log command displays all supported event types."""
    # Arrange
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    # Create all event types
    plan_block = create_plan_block(
        issue_number=42,
        worktree_name="test-plan",
        timestamp="2024-01-15T12:30:00Z",
    )

    submission_block = create_submission_queued_block(
        queued_at="2024-01-15T12:32:00Z",
        submitted_by="testuser",
        issue_number=42,
        validation_results={"issue_is_open": True},
        expected_workflow="implement-plan",
    )

    workflow_block = create_workflow_started_block(
        started_at="2024-01-15T12:35:00Z",
        workflow_run_id="123456",
        workflow_run_url="https://github.com/owner/repo/actions/runs/123456",
        issue_number=42,
    )

    status_block = create_implementation_status_block(
        status="in_progress",
        timestamp="2024-01-15T12:40:00Z",
    )

    comments = [
        render_metadata_block(plan_block),
        render_metadata_block(submission_block),
        render_metadata_block(workflow_block),
        render_metadata_block(status_block),
    ]

    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
        comments={42: comments},
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify all event types are displayed
        assert "Plan created" in result.output
        assert "Queued for execution" in result.output
        assert "GitHub Actions workflow started" in result.output
        assert "Implementation in progress" in result.output


def test_log_with_invalid_plan_identifier() -> None:
    """Test log command with non-existent plan identifier."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, fake_issues = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output


def test_log_multiple_status_updates() -> None:
    """Test log command with multiple implementation status updates."""
    # Arrange
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    # Create multiple status updates
    status1 = create_implementation_status_block(
        status="in_progress",
        timestamp="2024-01-15T12:30:00Z",
    )

    status2 = create_implementation_status_block(
        status="in_progress",
        timestamp="2024-01-15T12:35:00Z",
    )

    status3 = create_implementation_status_block(
        status="complete",
        timestamp="2024-01-15T12:40:00Z",
    )

    comments = [
        render_metadata_block(status1),
        render_metadata_block(status2),
        render_metadata_block(status3),
    ]

    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
        comments={42: comments},
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify status updates are shown
        assert "Implementation in progress" in result.output
        assert "Implementation complete" in result.output


def test_log_json_structure() -> None:
    """Test JSON output has correct structure with metadata."""
    # Arrange
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    submission_block = create_submission_queued_block(
        queued_at="2024-01-15T12:32:00Z",
        submitted_by="testuser",
        issue_number=42,
        validation_results={"issue_is_open": True},
        expected_workflow="implement-plan",
    )

    comment = render_metadata_block(submission_block)

    fake_issues = FakeGitHubIssues(
        issues={42: _make_issue_info(plan)},
        comments={42: [comment]},
    )
    store = GitHubPlanStore(fake_issues)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, plan_store=store, issues=fake_issues)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42", "--json"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        events = json.loads(result.output)
        assert len(events) == 1

        event = events[0]

        # Verify required fields
        assert "timestamp" in event
        assert "event_type" in event
        assert "metadata" in event

        # Verify metadata structure
        metadata = event["metadata"]
        assert metadata["status"] == "queued"
        assert metadata["submitted_by"] == "testuser"
        assert metadata["expected_workflow"] == "implement-plan"
