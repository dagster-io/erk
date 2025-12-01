"""Tests for plan log command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.plan_store.event_store import PlanEvent, PlanEventType
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.fake_event_store import FakePlanEventStore
from erk_shared.plan_store.types import Plan, PlanState

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_plan(plan_identifier: str = "42") -> Plan:
    """Create a Plan for testing."""
    return Plan(
        plan_identifier=plan_identifier,
        title="Test Plan",
        body="Implementation plan",
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{plan_identifier}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )


def test_log_displays_timeline_chronologically() -> None:
    """Test log command displays events in chronological order."""
    # Arrange
    plan = _make_plan()

    # Create events (intentionally out of order to test sorting in event store)
    event1 = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 15, 12, 30, 0, tzinfo=UTC),
        data={"worktree_name": "test-plan"},
    )
    event2 = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 15, 12, 32, 0, tzinfo=UTC),
        data={"submitted_by": "user", "status": "queued"},
    )
    event3 = PlanEvent(
        event_type=PlanEventType.WORKFLOW_STARTED,
        timestamp=datetime(2024, 1, 15, 12, 35, 0, tzinfo=UTC),
        data={"workflow_run_url": "https://github.com/owner/repo/actions/runs/123456"},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        event_store = FakePlanEventStore()
        # Append events out of order - event store sorts them
        event_store.append_event(env.cwd, "42", event3)
        event_store.append_event(env.cwd, "42", event1)
        event_store.append_event(env.cwd, "42", event2)

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Plan #42 Event Timeline" in result.output

        # Verify chronological order (plan created → queued → workflow started)
        output_lines = result.output.split("\n")
        event_lines = [line for line in output_lines if "[2024-" in line]

        assert len(event_lines) == 3
        assert "12:30:00" in event_lines[0]  # Created first
        assert "12:32:00" in event_lines[1]  # Queued second
        assert "12:35:00" in event_lines[2]  # Workflow started third


def test_log_json_output() -> None:
    """Test log command with --json flag outputs valid JSON."""
    # Arrange
    plan = _make_plan()
    event = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 15, 12, 30, 0, tzinfo=UTC),
        data={"worktree_name": "test-plan"},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        event_store = FakePlanEventStore()
        event_store.append_event(env.cwd, "42", event)

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42", "--json"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        events = json.loads(result.output)
        assert isinstance(events, list)
        assert len(events) == 1

        parsed_event = events[0]
        assert parsed_event["event_type"] == "plan_created"
        assert "2024-01-15" in parsed_event["timestamp"]
        assert parsed_event["metadata"]["worktree_name"] == "test-plan"


def test_log_with_no_events() -> None:
    """Test log command when plan has no events."""
    # Arrange
    plan = _make_plan()

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        event_store = FakePlanEventStore()  # No events

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No events found for plan #42" in result.output


def test_log_with_all_event_types() -> None:
    """Test log command displays all supported event types."""
    # Arrange
    plan = _make_plan()

    events = [
        PlanEvent(
            event_type=PlanEventType.CREATED,
            timestamp=datetime(2024, 1, 15, 12, 30, 0, tzinfo=UTC),
            data={"worktree_name": "test-plan"},
        ),
        PlanEvent(
            event_type=PlanEventType.QUEUED,
            timestamp=datetime(2024, 1, 15, 12, 32, 0, tzinfo=UTC),
            data={"submitted_by": "testuser", "status": "queued"},
        ),
        PlanEvent(
            event_type=PlanEventType.WORKFLOW_STARTED,
            timestamp=datetime(2024, 1, 15, 12, 35, 0, tzinfo=UTC),
            data={"workflow_run_url": "https://github.com/owner/repo/actions/runs/123456"},
        ),
        PlanEvent(
            event_type=PlanEventType.PROGRESS,
            timestamp=datetime(2024, 1, 15, 12, 40, 0, tzinfo=UTC),
            data={"status": "in_progress", "completed_steps": 3, "total_steps": 5},
        ),
    ]

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        event_store = FakePlanEventStore()
        for event in events:
            event_store.append_event(env.cwd, "42", event)

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify all event types are displayed
        assert "Plan created" in result.output
        assert "Queued for execution" in result.output
        assert "GitHub Actions workflow started" in result.output
        assert "Progress: 3/5 steps" in result.output


def test_log_with_invalid_plan_identifier() -> None:
    """Test log command with non-existent plan identifier."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={})
        event_store = FakePlanEventStore()

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output


def test_log_multiple_status_updates() -> None:
    """Test log command with multiple implementation status updates."""
    # Arrange
    plan = _make_plan()

    events = [
        PlanEvent(
            event_type=PlanEventType.PROGRESS,
            timestamp=datetime(2024, 1, 15, 12, 30, 0, tzinfo=UTC),
            data={"status": "in_progress", "completed_steps": 1, "total_steps": 5},
        ),
        PlanEvent(
            event_type=PlanEventType.PROGRESS,
            timestamp=datetime(2024, 1, 15, 12, 35, 0, tzinfo=UTC),
            data={"status": "in_progress", "completed_steps": 3, "total_steps": 5},
        ),
        PlanEvent(
            event_type=PlanEventType.COMPLETED,
            timestamp=datetime(2024, 1, 15, 12, 40, 0, tzinfo=UTC),
            data={"status": "complete", "completed_steps": 5, "total_steps": 5},
        ),
    ]

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        event_store = FakePlanEventStore()
        for event in events:
            event_store.append_event(env.cwd, "42", event)

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify all status updates are shown
        assert "Progress: 1/5 steps" in result.output
        assert "Progress: 3/5 steps" in result.output
        assert "Implementation complete" in result.output


def test_log_json_structure() -> None:
    """Test JSON output has correct structure with metadata."""
    # Arrange
    plan = _make_plan()
    event = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 15, 12, 32, 0, tzinfo=UTC),
        data={
            "status": "queued",
            "submitted_by": "testuser",
            "expected_workflow": "implement-plan",
        },
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        plan_store = FakePlanStore(plans={"42": plan})
        event_store = FakePlanEventStore()
        event_store.append_event(env.cwd, "42", event)

        ctx = build_workspace_test_context(env, plan_store=plan_store, plan_event_store=event_store)

        # Act
        result = runner.invoke(cli, ["plan", "log", "42", "--json"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        events = json.loads(result.output)
        assert len(events) == 1

        parsed_event = events[0]

        # Verify required fields
        assert "timestamp" in parsed_event
        assert "event_type" in parsed_event
        assert "metadata" in parsed_event

        # Verify metadata structure
        metadata = parsed_event["metadata"]
        assert metadata["status"] == "queued"
        assert metadata["submitted_by"] == "testuser"
        assert metadata["expected_workflow"] == "implement-plan"
